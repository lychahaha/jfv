import enum
import os
import pickle

op_chs = set(['(',')','|','&','!','=','#'])
op_adv = {'|':1,'&':2,'!':4,'==':3,'!=':3,'#':0}
op_func = {
    '|':lambda a,b : a or b,
    '&':lambda a,b : a and b,
    '!':lambda a : not a,
    '==':lambda a,b : a==b,
    '!=':lambda a,b : a!=b,
    '#':lambda a : a,
}

class TagSystem(object):
    def __init__(self, tag_filepath, img_extnames):
        self.tag_filepath = tag_filepath
        self.img_extnames = img_extnames

        self.tag_dict = {} #path->dict(k->v)
        self.is_dirty = False

        self.meta_tag_tree = [0,[]]
        self.meta_kvtag_list = []
        self.meta_tag2name = {}
        self.meta_tag_cnt = 1

        self.reset()

    def updateTag(self, path, tagDict):
        self.tag_dict[path] = tagDict
        self.is_dirty = True

    def getTag(self, path):
        return self.tag_dict[path]



    def addMetaTag(self, tagName, fatherTag):
        fatherNode,_ = self._dfs_find(fatherTag)
        assert fatherNode is not None, f'fatherTag({fatherTag}) not found'
        fatherNode[1].append([self.meta_tag_cnt,[]])
        self.meta_tag2name[self.meta_tag_cnt] = tagName
        self.meta_tag_cnt += 1
        self.is_dirty = True

    def removeMetaTag(self, tag):
        tagNode,fatherNode = self._dfs_find(tag)
        assert tagNode is not None, f'tag({tag}) not found'
        self._dfs_exec(tagNode, lambda cur_node:self.meta_tag2name.pop(cur_node[0]))
        ix = [k for k,son_node in enumerate(fatherNode[1]) if son_node[0] == tag][0]
        fatherNode.pop(ix)
        self.is_dirty = True

    def moveMetaTag(self, tag, dstFatherTag, dstBigBroTag):
        tagNode,fatherNode = self._dfs_find(tag)
        assert tagNode is not None, f'tag({tag}) not found'
        ix = [k for k,son_node in enumerate(fatherNode[1]) if son_node[0] == tag][0]
        fatherNode.pop(ix)
        dstFatherNode,_ = self._dfs_find(dstFatherTag)
        assert dstFatherNode is not None, f'dstFatherTag({dstFatherTag}) not found'
        if dstBigBroTag < 0:
            dstFatherNode[1].insert(0, tagNode)
        else:
            ix_bigbro = [k for k,son_node in enumerate(dstFatherNode[1]) if son_node[0] == dstBigBroTag]
            assert len(ix_bigbro)!=-1, f'dstBigBroTag({dstBigBroTag}) not found'
            ix_bigbro = ix_bigbro[0]
            dstFatherNode[1].insert(ix_bigbro+1, tagNode)
        self.is_dirty = True

    def renameMetaTag(self, tag, newName):
        assert tag in self.meta_tag2name, f'tag({tag}) not found'
        self.meta_tag2name[tag] = newName
        self.is_dirty = True

    def addMetaKVTag(self, tagName, bigBroTag):
        if bigBroTag < 0:
            self.meta_kvtag_list.insert(0, self.meta_tag_cnt)
        else:
            ix_bigbro = self.meta_kvtag_list.index(bigBroTag)
            assert ix_bigbro!=-1, f'bigBroTag({bigBroTag}) not found'
            self.meta_kvtag_list.insert(ix_bigbro+1, self.meta_tag_cnt)
        self.meta_tag_cnt += 1
        self.is_dirty = True

    def removeKVTag(self, tag):
        ix = self.meta_kvtag_list.index(tag)
        assert ix!=-1, f'tag({tag}) not found'
        self.meta_kvtag_list.pop(ix)
        self.is_dirty = True

    def moveMetaKVTag(self, tag, dstBigBroTag):
        ix = self.meta_kvtag_list.index(tag)
        assert ix!=-1, f'tag({tag}) not found'
        self.meta_kvtag_list.pop(ix)

        if dstBigBroTag < 0:
            self.meta_kvtag_list.insert(0, tag)
        else:
            ix_bigbro = self.meta_kvtag_list.index(dstBigBroTag)
            assert ix_bigbro!=-1, f'dstBigBroTag({dstBigBroTag}) not found'
            self.meta_kvtag_list.insert(ix_bigbro+1, tag)

        self.is_dirty = True

    def renameMetaKVTag(self, tag, newName):
        return self.renameMetaTag(tag, newName)

    def _dfs_find(self, tag):
        ret = (None,None)
        def dfs(cur_node,fa_node):
            if cur_node[0] == tag:
                ret = (cur_node,fa_node)
                return True
            for son_node in cur_node[1]:
                if dfs(son_node,cur_node):
                    return True
            return False

        ans = dfs(self.meta_tag_tree,None)
        return ret

    def _dfs_exec(self, node, func):
        def dfs(cur_node):
            func(cur_node)
            for son_node in cur_node[1]:
                dfs(son_node)
            return

        dfs(node)

    def save(self):
        data = [self.meta_tag_cnt,self.meta_tag_tree,self.meta_kvtag_list,self.meta_tag2name,self.tag_dict]
        pickle.dump(data, open(self.tag_filepath,'wb'))
        self.is_dirty = False

    def reset(self):
        if not os.path.exists(self.tag_filepath):
            self.save()
            return
        data = pickle.load(open(self.tag_filepath,'rb'))
        self.meta_tag_cnt,self.meta_tag_tree,self.meta_kvtag_list,self.meta_tag2name,self.tag_dict = data
        self.is_dirty = False

    def cleanData(self):
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
                if len(remove_tags) > 0:
                    self.is_dirty = True
        for path in remove_paths:
            self.tag_dict.pop(path)
        if len(remove_paths) > 0:
            self.is_dirty = True



    def filterImage(self, pathStr, tagStr):
        paths = self._filterImageByPath(pathStr)
        paths = self._filterImageByTagExp(paths, tagStr)
        return paths

    def _filterImageByPath(self, pathStr):
        ret_paths = []
        for cur_dir,dirs,files in os.walk(pathStr):
            for file in files:
                if os.path.splitext(file)[1] in self.img_extnames:
                    ret_paths.append(os.path.join(cur_dir, file))
        return ret_paths

    def _filterImageByTagExp(self, paths, tagStr):
        if tagStr == "":
            return paths

        tagStr = tagStr + '#'
        s1 = []
        s2 = []
        ibeg = 0
        while ibeg < len(tagStr):
            if tagStr[ibeg] in op_chs:
                if tagStr[ibeg] in ['=','!'] and ibeg+1<len(tagStr) and tagStr[ibeg+1]=='=':
                    iend = ibeg + 2
                else:
                    iend = ibeg + 1
                op = tagStr[ibeg:iend]
                if op == '(':
                    s1.append([1,op])
                elif op == ')':
                    while s1[-1][1] != '(':
                        s2.append(s1[-1])
                        s1.pop()
                else:
                    while len(s1)>0 and op_adv[s1[-1][1]]>=op_adv[op]:
                        s2.append(s1[-1])
                        s1.pop()
                    s1.append([1,op])
                ibeg = iend
            else:
                iend = ibeg + 1
                while iend < len(tagStr) and tagStr[iend] not in op_chs:
                    iend += 1
                s2.append([0,tagStr[ibeg:iend]])
                ibeg = iend
        s2.append([1,'#'])

        ret_paths = []
        for path in paths:
            s = []
            for code,item in s2:
                if code == 0:
                    s.append([item])
                else:
                    if item in ['!','#']:
                        num1 = s.pop()
                        val1 = num1[0] in self.tag_dict[path] if isinstance(num1, list) else num1
                        s.append(op_func[item](val1))
                    else:
                        num2 = s.pop()
                        num1 = s.pop()
                        if item in ['==','!=']:
                            if isinstance(num1, list):
                                if num1[0] in self.tag_dict[path]:
                                    val1 = self.tag_dict[path][num1[0]]
                                else:
                                    val1 = None
                            else:
                                val1 = num1
                            val2 = num2[0]
                        else:
                            val1 = num1[0] in self.tag_dict[path] if isinstance(num1, list) else num1
                            val2 = num2[0] in self.tag_dict[path] if isinstance(num2, list) else num2
                        s.append(op_func[item](val1,val2))

            if s[0]:
                ret_paths.append(path)
        
        return ret_paths
