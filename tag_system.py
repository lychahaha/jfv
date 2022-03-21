import os
import pickle
import copy
import datetime
import re

'''
TagSystem模块可独立于Qt/GUI使用

该模块主要负责三项任务：
    1. 管理标签信息
    2. 管理标签文件
    3. 实现标签筛选算法

名词解释：
    1. 元标签：标签树上的单元
    2. 标签：一般指某个图片包含的元标签
    3. 标签码：元标签的唯一识别码
    4. 标签名字：元标签的名字    
    5. KV元标签：带值的元标签（标签码作为键）
    6. 标签树和KV标签列表：普通元标签是以树为数据结构，KV标签是以链表为结构

标签树结构：
    1. 该结构是多叉树
    2. 根在TagWidget是不显示的
    3. 根的儿子是TagWidget的顶层节点

标签筛选算法
    事实上，目前有三级筛选：
    1. 路径目录
    2. 路径筛选
    3. 标签筛选
    2和3的筛选都写在了tagStr中，格式是{pathFilterStr}tagFilterStr

    pathFilterStr为正则表达式
    tagFilterStr为逻辑表达式，支持与或非，以及等于不等（用于KV标签），例如：
        坐姿&逆光|!俯拍
        蹲姿&光圈==F1.4
'''

# 标签筛选用到的东西
op_chs = set(['(',')','|','&','!','=','#']) #属于op的字符
op_adv = {'|':1,'&':2,'!':4,'==':3,'!=':3,'#':0} #op优先级
op_func = { #op具体函数
    '|':lambda a,b : a or b,
    '&':lambda a,b : a and b,
    '!':lambda a : not a,
    '==':lambda a,b : a==b,
    '!=':lambda a,b : a!=b,
    '#':lambda a : a,
}

class TagSystem(object):
    def __init__(self, tag_filedir, img_extnames):
        self.tag_filedir = tag_filedir #保存标签文件的目录
        self.img_extnames = img_extnames #需要打标签的图片文件名后缀

        self.tag_dict = {} #path->dict(k->v) 每个图片对应的标签集，k是标签码，v是KV标签值，普通标签的v为None
        self.is_dirty = False #判断是否修改（即是否未保存）

        self.meta_tag_tree = [0,[]] #标签树数据结构，节点第一项是标签码，第二项是儿子节点列表
        self.meta_kvtag_list = [] #list(int) KV标签列表数据结构
        self.meta_tag2name = {0:'root'} #标签码->标签名字
        self.meta_tag_cnt = 1 #标签码最大值（用于分配新标签码）

        self.reset() #从文件载入标签数据

    def updateTag(self, path, tagDict):
        '''
        tag的set操作
        args
            path: str 图片路径
            tagDict: dict(k->v) 图片标签集
        '''
        self.tag_dict[path] = copy.deepcopy(tagDict)
        self.is_dirty = True

    def getTag(self, path):
        '''
        tag的get操作
        args
            path: str 图片路径
        ret 
            dict(k->v) 图片标签集
        '''
        if path not in self.tag_dict:
            return {}
        else:
            return copy.deepcopy(self.tag_dict[path])

    def getTagName(self, tag):
        '''
        获取元标签标签码对应的名字
        args
            tag:int 标签码
        ret
            str 名字
        '''
        return self.meta_tag2name[tag]

    def addMetaTag(self, tagName, fatherTag):
        '''
        添加元标签
        args
            tagName: str 新标签名字
            fatherTag: int 父亲标签码
        ret
            int 新的元标签的标签码
        '''
        fatherNode,_ = self._dfs_find(fatherTag)
        assert fatherNode is not None, f'fatherTag({fatherTag}) not found'
        fatherNode[1].append([self.meta_tag_cnt,[]])
        self.meta_tag2name[self.meta_tag_cnt] = tagName
        self.meta_tag_cnt += 1
        self.is_dirty = True
        return self.meta_tag_cnt - 1

    def removeMetaTag(self, tag):
        '''
        删除元标签
        会同时删除该元标签的所有子孙
        args
            tag: int 元标签的标签码
        '''
        tagNode,fatherNode = self._dfs_find(tag)
        assert tagNode is not None, f'tag({tag}) not found'
        self._dfs_exec(tagNode, lambda cur_node:self.meta_tag2name.pop(cur_node[0])) #删除所有子孙
        ix = [k for k,son_node in enumerate(fatherNode[1]) if son_node[0] == tag][0]
        fatherNode[1].pop(ix)
        self.is_dirty = True

    def moveMetaTag(self, tag, dstFatherTag, dstBigBroTag):
        '''
        在标签树上移动元标签
        移动以该元标签的整棵子树
        args
            tag: int 元标签的标签码
            dstFatherTag: int 目标父亲的标签码（由于根是不显示的，因此可见节点必定有父亲）
            dstBigBroTag: int 目标哥哥的标签码（如果是大哥，则该值是负数）
        '''
        tagNode,fatherNode = self._dfs_find(tag)
        assert tagNode is not None, f'tag({tag}) not found'
        ix = [k for k,son_node in enumerate(fatherNode[1]) if son_node[0] == tag][0]
        fatherNode[1].pop(ix)
        dstFatherNode,_ = self._dfs_find(dstFatherTag)
        assert dstFatherNode is not None, f'dstFatherTag({dstFatherTag}) not found'
        if dstBigBroTag < 0:
            # 自己是大哥
            dstFatherNode[1].insert(0, tagNode)
        else:
            # 自己不是大哥
            ix_bigbro = [k for k,son_node in enumerate(dstFatherNode[1]) if son_node[0] == dstBigBroTag]
            assert len(ix_bigbro)!=0, f'dstBigBroTag({dstBigBroTag}) not found'
            ix_bigbro = ix_bigbro[0]
            dstFatherNode[1].insert(ix_bigbro+1, tagNode)
        self.is_dirty = True

    def renameMetaTag(self, tag, newName):
        '''
        重命名元标签
        args
            tag: int 元标签的标签码
            newName: str 元标签的新名字
        '''
        assert tag in self.meta_tag2name, f'tag({tag}) not found'
        self.meta_tag2name[tag] = newName
        self.is_dirty = True

    def addMetaKVTag(self, tagName, bigBroTag):
        '''
        新增一个KV元标签
        args
            tagName:str 新KV元标签的名字
            bigBroTag:int 目标哥哥的标签码
        ret int 新KV元标签的标签码
        '''
        if bigBroTag < 0:
            # 自己是大哥
            self.meta_kvtag_list.insert(0, self.meta_tag_cnt)
        else:
            # 自己不是大哥
            ix_bigbro = self.meta_kvtag_list.index(bigBroTag)
            assert ix_bigbro!=-1, f'bigBroTag({bigBroTag}) not found'
            self.meta_kvtag_list.insert(ix_bigbro+1, self.meta_tag_cnt)
        self.meta_tag2name[self.meta_tag_cnt] = tagName
        self.meta_tag_cnt += 1
        self.is_dirty = True
        return self.meta_tag_cnt - 1

    def removeKVTag(self, tag):
        '''
        删除KV元标签
        args
            tag:int 目标元标签的标签码
        '''
        ix = self.meta_kvtag_list.index(tag)
        assert ix!=-1, f'tag({tag}) not found'
        self.meta_kvtag_list.pop(ix)
        self.is_dirty = True

    def moveMetaKVTag(self, tag, dstBigBroTag):
        '''
        移动KV元标签
        args
            tag:int 目标元标签的标签码
            dstBigBrotag:int 目标哥哥的标签码
        '''
        ix = self.meta_kvtag_list.index(tag)
        assert ix!=-1, f'tag({tag}) not found'
        self.meta_kvtag_list.pop(ix)

        if dstBigBroTag < 0:
            # 自己是大哥
            self.meta_kvtag_list.insert(0, tag)
        else:
            # 自己不是大哥
            ix_bigbro = self.meta_kvtag_list.index(dstBigBroTag)
            assert ix_bigbro!=-1, f'dstBigBroTag({dstBigBroTag}) not found'
            self.meta_kvtag_list.insert(ix_bigbro+1, tag)

        self.is_dirty = True

    def renameMetaKVTag(self, tag, newName):
        '''
        重命名KV元标签
        args
            tag:int 目标元标签的标签码
            newName:str 新名字
        '''
        return self.renameMetaTag(tag, newName)

    def _dfs_find(self, tag):
        '''
        在标签树上搜索元标签
        args
            tag:int 目标元标签的标签码
        ret (node,node) 返回目标标签的节点，以及它的父亲。没找到则返回(None,None)
        '''
        ret = (None,None)
        def dfs(cur_node,fa_node):
            if cur_node[0] == tag:
                nonlocal ret
                ret = (cur_node,fa_node)
                return True
            for son_node in cur_node[1]:
                if dfs(son_node,cur_node):
                    return True
            return False

        ans = dfs(self.meta_tag_tree,None)
        return ret

    def _dfs_exec(self, node, func):
        '''
        以标签树上的某个节点为根，遍历这棵子树，对每个节点进行某种操作
        args
            node:node 目标根节点
            func:func 操作函数
        '''
        def dfs(cur_node):
            func(cur_node)
            for son_node in cur_node[1]:
                dfs(son_node)
            return

        dfs(node)

    def save(self):
        '''
        保存数据（包括一个储存标签的dict，和4个关于元标签的结构）
        将数据保存到文件里
        '''
        data = [self.meta_tag_cnt,self.meta_tag_tree,self.meta_kvtag_list,self.meta_tag2name,self.tag_dict]
        os.makedirs(self.tag_filedir, exist_ok=True)
        pickle.dump(data, open(os.path.join(self.tag_filedir,'tag.pkl'),'wb'))
        self.is_dirty = False

    def auto_save(self):
        '''
        自动保存数据
        和save的区别主要是路径上加上了时间
        '''
        data = [self.meta_tag_cnt,self.meta_tag_tree,self.meta_kvtag_list,self.meta_tag2name,self.tag_dict]
        time_str = datetime.datetime.strftime(datetime.datetime.now(), "%Y_%m_%d_%H_%M_%S")
        auto_save_path = os.path.join(self.tag_filedir,f'tag_{time_str}.pkl')
        os.makedirs(self.tag_filedir, exist_ok=True)
        pickle.dump(data, open(auto_save_path,'wb'))

    def reset(self):
        '''
        重设数据
        save的逆操作，从文件里读取数据
        '''
        # 如果没有该文件，则保存
        if not os.path.exists(os.path.join(self.tag_filedir,'tag.pkl')):
            self.save()
            return
        data = pickle.load(open(os.path.join(self.tag_filedir,'tag.pkl'),'rb'))
        self.meta_tag_cnt,self.meta_tag_tree,self.meta_kvtag_list,self.meta_tag2name,self.tag_dict = data
        self.is_dirty = False

    def cleanData(self):
        '''
        清理数据
        包括两类：
            1. 文件不存在，但tag_dict里还有该文件数据
            2. 元标签不存在，但tag_dict里某些文件还有对应的标签数据
        '''
        remove_paths = []
        for path in self.tag_dict:
            if not os.path.exists(path):
                remove_paths.append(path)
            else:
                remove_tags = []
                for tag in self.tag_dict[path]:
                    if tag not in self.meta_tag2name:
                        remove_tags.append(tag)
                for tag in remove_tags:
                    self.tag_dict[path].pop(tag)
                if len(self.tag_dict[path]) == 0: #删到没有标签了
                    remove_paths.append(path)
                if len(remove_tags) > 0:
                    self.is_dirty = True
        for path in remove_paths:
            self.tag_dict.pop(path)
        if len(remove_paths) > 0:
            self.is_dirty = True

    def printMetaTagTree(self):
        '''
        打印标签树（debug用）
        '''
        def dfs(cur_node, deep):
            print("  "*deep, end='')
            print(f"{cur_node[0]}:{self.meta_tag2name[cur_node[0]]}")
            for son_node in cur_node[1]:
                dfs(son_node, deep+1)
        dfs(self.meta_tag_tree, 0)

    def filterImage(self, pathStr, tagStr):
        '''
        标签筛选算法的入口函数
        args
            pathStr:str 路径串
            tagStr:str 标签筛选串
        ret [str] 符合筛选要求的路径列表
        '''
        paths = self._filterImageByPath(pathStr)
        paths = self._filterImageByTagExp(paths, tagStr)
        return paths

    def _filterImageByPath(self, pathStr):
        '''
        查找路径目录里的所有子孙图片文件
        args
            pathStr:str 路径串
        ret [str] 符合筛选要求的路径列表
        '''
        ret_paths = []
        for cur_dir,dirs,files in os.walk(pathStr): #注意不单是本目录，还包括子孙目录的图片文件
            for file in files:
                if os.path.splitext(file)[1] in self.img_extnames:
                    ret_paths.append(os.path.join(cur_dir, file))
        return ret_paths

    def _filterImageByTagExp(self, paths, tagStr):
        '''
        筛选符合标签筛选串的所有图片文件
        先进行路径筛选，再进行标签筛选
        路径筛选使用正则表达式模块计算，标签筛选使用逆波兰表达式计算
        args
            paths: [str] 路径目录给出的所有图片文件的路径
            tagStr:str 标签筛选串
        ret [str] 符合筛选要求的路径列表
        '''
        # 特判空串（路径和标签都空）
        if tagStr == "":
            return paths

        # 判断是否有路径筛选串
        if tagStr[0] == '{':
            ix = tagStr.find('}')
            assert ix!=-1, f'invalid tagStr({tagStr})'
            paths = self._filterImageByPathExp(paths, tagStr[1:ix]) #路径筛选
            tagStr = tagStr[ix+1:]

        #特判空串（标签空）
        if tagStr == "":
            return paths

        name2tag = {name:tag for tag,name in self.meta_tag2name.items()} #tag2name的逆映射，下面算法会用到

        # 中序表达式转后缀表达式（逆波兰表达式）
        tagStr = tagStr + '#' #用于保证表达式结束
        s1 = []
        s2 = []
        ibeg = 0
        while ibeg < len(tagStr):
            if tagStr[ibeg] in op_chs: #运算符
                # 先确定运算符长度
                if tagStr[ibeg] in ['=','!'] and ibeg+1<len(tagStr) and tagStr[ibeg+1]=='=':
                    iend = ibeg + 2
                else:
                    iend = ibeg + 1
                op = tagStr[ibeg:iend]
                # 判断运算符类型
                if op == '(': # (
                    s1.append([1,op])
                elif op == ')': # )
                    while s1[-1][1] != '(':
                        s2.append(s1[-1])
                        s1.pop()
                else: # & | ! == !=
                    while len(s1)>0 and op_adv[s1[-1][1]]>=op_adv[op]:
                        s2.append(s1[-1])
                        s1.pop()
                    s1.append([1,op])
                ibeg = iend
            else: #标签或值
                iend = ibeg + 1
                while iend < len(tagStr) and tagStr[iend] not in op_chs:
                    iend += 1
                s2.append([0,name2tag[tagStr[ibeg:iend]]]) #名字转标签码
                ibeg = iend
        s2.append([1,'#']) #最后的#是不会进入s2的，要补充

        #计算逆波兰表达式的值
        ret_paths = []
        for path in paths: #对每个路径单独计算布尔值
            s = []
            for code,item in s2:
                if code == 0: #标签或值
                    s.append([item]) #先用列表形式，因为不确定是标签还是值，要等实际运算时才能进行正确转换
                else: #运算符
                    if item in ['!','#']: #单目运算符
                        num1 = s.pop()
                        val1 = path in self.tag_dict and num1[0] in self.tag_dict[path] if isinstance(num1, list) else num1 #如果是标签，则转为值
                        s.append(op_func[item](val1))
                    else: #双目运算符
                        num2 = s.pop()
                        num1 = s.pop()
                        if item in ['==','!=']: #要求==和!=的左边是标签，右边是值
                            if isinstance(num1, list):
                                if path in self.tag_dict and num1[0] in self.tag_dict[path]:
                                    val1 = self.tag_dict[path][num1[0]]
                                else:
                                    val1 = None
                            else:
                                val1 = num1
                            val2 = num2[0]
                        else: #其他双目运算符则要求两边都是标签
                            val1 = path in self.tag_dict and num1[0] in self.tag_dict[path] if isinstance(num1, list) else num1
                            val2 = path in self.tag_dict and num2[0] in self.tag_dict[path] if isinstance(num2, list) else num2
                        s.append(op_func[item](val1,val2))

            # 判断结果
            if s[0]:
                ret_paths.append(path)
        
        return ret_paths

    def _filterImageByPathExp(self, paths, pathFilterStr):
        '''
        路径筛选
        使用正则表达式模块计算
        args
            paths: [str] 路径目录给出的所有图片文件的路径
            pathFilterStr:str 路径筛选串
        ret [str] 符合筛选要求的路径列表
        '''
        ret_paths = []
        for path in paths:
            ma = re.search(pathFilterStr, path)
            if ma is not None:
                ret_paths.append(path)
        return ret_paths
