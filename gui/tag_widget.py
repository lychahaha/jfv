from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

'''
TagWidget
|-TagTree 标签树
|-saveBtn 保存按钮（它能否点击与TagSystem的脏位挂钩）
|-resetBtn 重设按钮（能否点击同saveBtn）
|
|-menu 右键菜单
    |-添加标签
    |-删除标签
    |-重命名

焦点与标签树
    TagTree的状态会与ViewWidget的焦点部件同步，包括：
    1. 是否显示checkbox（不显示说明焦点非法，包括没焦点、焦点包括非图片文件和目录）
    2. 标签信息（当焦点为多个图片时，checkbox有可能出现[部分选择]的情况，也就是不同图片的标签信息不同）
'''

class TagWidget(QDockWidget):
    def __init__(self, title, parent):
        super().__init__(title, parent)

        self.tag2item = {} #标签码->grid item
        self.tagTree = TagTree(self)
        
        self.menu = QMenu(self.tagTree)
        self.addTagAction = QAction("添加标签")
        self.removeTagAction = QAction("删除标签")
        self.renameTagAction = QAction('重命名')
        self.menu.addAction(self.addTagAction)
        self.menu.addAction(self.removeTagAction)
        self.menu.addAction(self.renameTagAction)
        self.tagTree.customContextMenuRequested.connect(self.slotMenuPopup) #右键菜单信号连接

        self.remake_tree() #初始化tagTree，载入数据

        self.saveBtn = QPushButton('保存')
        self.resetBtn = QPushButton('重设')
        self.saveBtn.setEnabled(False) #刚开始脏位不脏
        self.resetBtn.setEnabled(False)

        self.content = QWidget()
        layout2 = QHBoxLayout()
        layout2.addWidget(self.saveBtn)
        layout2.addWidget(self.resetBtn)
        layout1 = QVBoxLayout(self.content)
        layout1.addWidget(self.tagTree)
        layout1.addLayout(layout2)        
        self.setWidget(self.content)

        self.tagTree.itemCheckStateChanged.connect(self.slotItemCheckStateChanged) #tagtree的checkbox修改的信号连接
        self.saveBtn.clicked.connect(self.slotSave)
        self.resetBtn.clicked.connect(self.slotReset)

    def slotItemCheckStateChanged(self, item):
        '''
        tagTree的checkbox被点击的假槽
        该槽被调用，表明点击是合法的，即不存在
            1. 点击非文件的tag
            2. 没有焦点图片时点击tag
        args
            item:TagTreeItem 被点击的元标签item
        '''
        # 获取标签信息
        print(item.text(0), item.checkState(0))
        assert item.checkState(0) != Qt.PartiallyChecked, f"unexpect PartiallyChecked({item.text()})" #不应该点击成部分选中
        tag_state = True if item.checkState(0) == Qt.Checked else False
        tag = item.data(0, Qt.UserRole)

        #获取路径
        tag_system = self.parent().tag_system
        paths = self._get_cur_focus_paths()
        assert len(paths)!=0, "slotItemCheckStateChanged but len of paths is zero"
        #更新tag信息
        for path in paths:
            tagSet = tag_system.getTag(path)
            if tag_state and tag not in tagSet:
                tagSet[tag] = None
            elif not tag_state and tag in tagSet:
                tagSet.pop(tag)
            tag_system.updateTag(path, tagSet)
        # 更新脏位相关的GUI部件状态
        self.saveBtn.setEnabled(True)
        self.resetBtn.setEnabled(True)
        # 更新其他GUI部件
        self.parent().infoWidget.fill_tag_info()

    def slotSave(self):
        '''
        点击save按钮的槽
        '''
        self.parent().tag_system.save()
        self.saveBtn.setEnabled(False)
        self.resetBtn.setEnabled(False)

    def slotReset(self):
        '''
        点击reset按钮的槽
        '''
        # 先询问是否真的reset
        result = QMessageBox.question(self, '重设', '你确定要重设吗？')
        if result != QMessageBox.Yes:
            return
        # 先reset数据结构，再reset图形界面
        self.parent().tag_system.reset()
        self.remake_tree()
        
        self.saveBtn.setEnabled(False)
        self.resetBtn.setEnabled(False)

    def slotMenuPopup(self, pos):
        '''
        右键菜单的槽
        args
            pos: Qsize 右键点击的位置
        '''
        # 设置菜单项的可用
        item = self.tagTree.itemAt(pos)
        if item is None:
            # 如果点击的是空白，则删除和重命名是灰色
            self.removeTagAction.setEnabled(False)
            self.renameTagAction.setEnabled(False)
        else:
            # 否则，则可用
            self.removeTagAction.setEnabled(True)
            self.renameTagAction.setEnabled(True)
        # 执行
        action = self.menu.exec_(self.tagTree.mapToGlobal(pos))
        # 根据点击的项执行命令
        if action is self.addTagAction:
            self.slotAddMetaTag(item)
        elif action is self.removeTagAction:
            self.slotRemoveMetaTag(item)
        elif action is self.renameTagAction:
            self.slotRenameMetaTag(item)

    def slotAddMetaTag(self, fatherItem):
        '''
        右键菜单新增元标签的假槽
        args
            fatherItem:TagTreeItem|None 父亲GUI item
        '''
        # 弹窗获取新元标签的名字
        ok,newTagName = self._execAddMetaTagDialog()
        if not ok or newTagName == "":
            return

        # 判断是否是顶层标签
        if fatherItem is None:
            newTag = self.parent().tag_system.addMetaTag(newTagName, 0)
            newItem = TagTreeItem()
            self.tagTree.addTopLevelItem(newItem)
        else:
            newTag = self.parent().tag_system.addMetaTag(newTagName, fatherItem.data(0, Qt.UserRole))
            newItem = TagTreeItem(fatherItem)
        # 更新新标签的GUI状态
        newItem.setCheckState(0, Qt.Unchecked)
        newItem.setData(0, Qt.UserRole, newTag)
        newItem.setText(0, newTagName)
        self.tag2item[newTag] = newItem

        # 更新其他GUI部件
        self.fill_value() #重新载入标签树状态（主要是当前焦点非法时要将新标签修改成非法状态）
        self.saveBtn.setEnabled(True)
        self.resetBtn.setEnabled(True)
        self.printInfo()

    def slotRemoveMetaTag(self, item):
        '''
        右键菜单删除元标签的假槽
        args
            item:TagTreeItem 目标GUI item
        '''
        # 先询问是否要删除
        result = QMessageBox.question(self, '删除标签', f'你确定删除标签（{item.text(0)}）吗？')
        if result != QMessageBox.Yes:
            return
        # 执行删除
        tag = item.data(0, Qt.UserRole)
        self.parent().tag_system.removeMetaTag(tag)
        self.tag2item.pop(tag)
        fatherItem = item.parent()
        if fatherItem is None: #顶层标签特判
            self.tagTree.takeTopLevelItem(self.tagTree.indexOfTopLevelItem(item))
        else:
            fatherItem.removeChild(item)
        # 更新其他GUI部件
        self.saveBtn.setEnabled(True)
        self.resetBtn.setEnabled(True)
        self.printInfo()

    def slotMoveMetaTag(self, item, fa_item, bro_item):
        '''
        拖拽元标签的假槽
        调用该假槽，表明该移动是合法的，而不是原封不动，错误移动等
        执行该函数时，GUI item其实应该移动完毕，这里只是执行数据结构的移动
        args
            item:TagTreeItem 目标GUI item
            fa_item:TagTreeItem|None 目标父亲GUI item
            bro_item:TagTreeItem|None 目标哥哥GUI item
        '''
        tag = item.data(0, Qt.UserRole)
        fa_tag = fa_item.data(0, Qt.UserRole) if fa_item is not None else 0
        bro_tag = bro_item.data(0, Qt.UserRole) if bro_item is not None else -1
        self.parent().tag_system.moveMetaTag(tag, fa_tag, bro_tag)

        self.saveBtn.setEnabled(True)
        self.resetBtn.setEnabled(True)
        self.printInfo()

    def slotRenameMetaTag(self, item):
        '''
        右键菜单重命名元标签的假槽
        args
            item:TagTreeItem 目标GUI item
        '''
        # 先弹窗询问新名字
        ok,newTagName = self._execRanameMetaTagDialog(item.text(0))
        if not ok or newTagName == "":
            return
        # 执行重命名
        tag = item.data(0, Qt.UserRole)
        self.parent().tag_system.renameMetaTag(tag, newTagName)
        item.setText(0, newTagName)
        # 更新其他GUI部件
        self.saveBtn.setEnabled(True)
        self.resetBtn.setEnabled(True)
        self.printInfo()

    def _execAddMetaTagDialog(self):
        '''
        弹窗询问新增标签的名字
        ret
            bool 是否点击了确认
            str 新标签的名字
        '''
        dialog = QInputDialog()
        dialog.setWindowTitle('添加标签')
        dialog.setLabelText('请输入新标签')
        dialog.setOkButtonText('确定')
        dialog.setCancelButtonText('取消')
        ret = dialog.exec_()
        return ret,dialog.textValue()

    def _execRanameMetaTagDialog(self, old_name):
        '''
        弹窗询问标签的新名字
        ret
            bool 是否点击了确认
            str 标签的新名字
        '''
        dialog = QInputDialog()
        dialog.setWindowTitle('重命名')
        dialog.setLabelText('请输入标签的新名字')
        dialog.setOkButtonText('确定')
        dialog.setCancelButtonText('取消')
        dialog.setTextValue(old_name)
        ret = dialog.exec_()
        return ret,dialog.textValue()

    def remake_tree(self):
        '''
        重构标签树GUI，包括
        1. 元标签树的树结构
        2. 元标签的checkbox状态
        '''
        tag_system = self.parent().tag_system

        def dfs(cur_node, deep):
            for son_node in cur_node[1]:
                if deep == 0: #顶层判断
                    son_item = TagTreeItem()
                    self.tagTree.addTopLevelItem(son_item)
                else:
                    son_item = TagTreeItem(self.tag2item[cur_node[0]])
                son_item.setCheckState(0, Qt.Unchecked) #启用checkbox
                son_item.setData(0, Qt.UserRole, son_node[0]) #标签码
                son_item.setText(0, tag_system.meta_tag2name[son_node[0]]) #标签名字
                self.tag2item[son_node[0]] = son_item #维护dict
                dfs(son_node, deep+1)

        self.tag2item = {}
        self.tagTree.clear() #先全部清除
        dfs(tag_system.meta_tag_tree, 0)
        self.tagTree.expandAll() #展开所有子项
        self.fill_value()

    def fill_value(self):
        '''
        根据viewWidget的焦点grid设置元标签的checkbox状态，包括：
        1. 是否非法
        2. 合法时的三种状态（选中，部分选中，没选中）
        '''
        self.tagTree.push_close_signal() #关闭信号，避免发送checkbox修改信号

        # 判断焦点合法性
        paths = self._get_cur_focus_paths()
        if paths is None:
            self._set_checkbox_disabled() #非法
            self.tagTree.pop_signal() #打开信号
            return

        tag_system = self.parent().tag_system
        path2set = {path:tag_system.getTag(path) for path in paths}

        for tag,item in self.tag2item.items():
            # 获取所有焦点的标签信息
            result = set()
            for path,tagSet in path2set.items():
                result.add(tag in tagSet)
            assert len(result) in [1,2], f'unexpect len of result({result})'
            # 根据信息进行checkbox状态设置
            if len(result) == 2:
                item.setCheckState(0, Qt.PartiallyChecked)
            elif len(result) == 1:
                if result.pop():
                    item.setCheckState(0, Qt.Checked)
                else:
                    item.setCheckState(0, Qt.Unchecked)

        self.tagTree.pop_signal() #打开信号

    def printInfo(self):
        '''
        打印标签树（debug用）
        '''
        print(self.tag2item.keys())
        if self.parent().global_args['debug']:
            self.parent().tag_system.printMetaTagTree()

    def _get_cur_focus_paths(self):
        '''
        获取当前viewWidget的所有焦点grid的路径
        有下列情况时，均返回None表示焦点非法：
        1. 焦点含有非图片文件
        2. 没有焦点
        ret
            [str]|None 焦点grid的路径列表
        '''
        cur_focus = self.parent().viewWidget.cur_focus
        img_paths = [g.path for g in cur_focus if g.filetype=='img']
        if len(cur_focus) != len(img_paths):
            return None
        if len(img_paths) == 0:
            return None
        return img_paths

    def _set_checkbox_disabled(self):
        '''
        将所有checkbox设置成非法状态
        '''
        for tag in self.tag2item:
            self.tag2item[tag].setData(0, Qt.CheckStateRole, None)

    
class TagTreeItem(QTreeWidgetItem):
    def setData(self, column, role, value):
        '''
        tract setData
        在setData时判断是否是合法的checkbox点击，并发送信号
        包括以下判断：
        1. 是否是关闭信号状态（fill_value时会关闭信号来setData，避免误判成用户点击checkbox）
        2. 是否是checkbox被修改
        3. 是否是checkbox第一次被启用
        4. checkbox的值有没有改变
        '''
        
        is_check_changed = self.treeWidget().is_signal_open() and \
                           column==0 and \
                           role==Qt.CheckStateRole and \
                           self.data(column, role) is not None and \
                           self.checkState(0)!=value
        ret = super().setData(column, role, value) #先执行原有操作
        if is_check_changed:
            self.treeWidget().itemCheckStateChanged.emit(self)
        return ret

class TagTree(QTreeWidget):
    # 由于QTreeWidget原有的itemChanged信号覆盖范围非常广，因此新增一信号，来处理checkbox点击情况
    itemCheckStateChanged = pyqtSignal(TagTreeItem) 

    def __init__(self, tagView):
        super().__init__()

        self.tagView = tagView

        # 用来处理fill_value时的关闭/打开信号
        self.signal_stack = [True]
        self.enter_items = []

        self.setHeaderHidden(True) #隐藏表头
        self.setContextMenuPolicy(Qt.CustomContextMenu) #设置右键菜单可用
        self.setAcceptDrops(True) #？
        self.setDragEnabled(True) #设置可拖拽
        self.setDragDropMode(QAbstractItemView.InternalMove) #？

    def mousePressEvent(self, e):
        '''
        鼠标点击时，记录拖拽会用到的相关信息
        '''
        if e.button() == Qt.LeftButton:
            item = self.itemAt(e.pos())
            fa_item,bro_item = self._get_fa_and_bro_item(item)
            self.enter_items = [item,fa_item,bro_item]

        return super().mousePressEvent(e)

    def dropEvent(self, e):
        '''
            拖拽事件的处理
            判断是否合法拖拽（即拖拽是否真的改变了标签树的结构），并往上调用假槽
        '''
        ret = super().dropEvent(e)
        item,old_fa_item,old_bro_item = self.enter_items
        if item is not None:
            new_fa_item,new_bro_item = self._get_fa_and_bro_item(item)
            if old_fa_item is new_fa_item and old_bro_item is new_bro_item:
                pass
            else:
                self.tagView.slotMoveMetaTag(item, new_fa_item, new_bro_item)
        return ret

    def pop_signal(self):
        '''
        启用信号（事实上是弹栈，不一定是启用）
        '''
        self.signal_stack.pop(-1)

    def push_close_signal(self):
        '''
        关闭信号（压栈）
        '''
        self.signal_stack.append(False)

    def is_signal_open(self):
        '''
        判断信号是否打开
        ret
            bool
        '''
        return self.signal_stack[-1]

    def _get_fa_and_bro_item(self, item):
        '''
        获取目标item的父亲和哥哥item
        args
            item:TagTreeItem 目标item
        ret
            fa_item:TagTreeItem 目标item的父亲
            bro_item:TagTreeItem 目标item的哥哥
        '''
        if item is None:
            fa_item = bro_item = None
        else:
            fa_item = item.parent()
            if fa_item is None:
                bro_item = self.topLevelItem(self.indexOfTopLevelItem(item)-1)
            else:
                bro_item = fa_item.child(fa_item.indexOfChild(item)-1)
        return fa_item,bro_item
