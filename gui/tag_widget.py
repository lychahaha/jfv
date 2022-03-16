from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class TagWidget(QDockWidget):
    def __init__(self, title, parent):
        super().__init__(title, parent)

        self.tagTree = TagTree(self)
        
        self.menu = QMenu(self.tagTree)
        self.addTagAction = QAction("添加标签")
        self.removeTagAction = QAction("删除标签")
        self.menu.addAction(self.addTagAction)
        self.menu.addAction(self.removeTagAction)
        self.tagTree.customContextMenuRequested.connect(self.slotMenuPopup)

        self.remake_tree()
        self.tagTree.expandAll()

        self.tag2item = {}

        self.saveBtn = QPushButton('保存')
        self.resetBtn = QPushButton('重设')
        self.saveBtn.setEnabled(False)
        self.resetBtn.setEnabled(False)

        self.content = QWidget()
        layout2 = QHBoxLayout()
        layout2.addWidget(self.saveBtn)
        layout2.addWidget(self.resetBtn)
        layout1 = QVBoxLayout(self.content)
        layout1.addWidget(self.tagTree)
        layout1.addLayout(layout2)        
        self.setWidget(self.content)

        self.tagTree.itemCheckStateChanged.connect(self.slotItemCheckStateChanged)
        self.saveBtn.clicked.connect(self.slotSave)
        self.resetBtn.clicked.connect(self.slotReset)

    def slotItemCheckStateChanged(self, item):
        print(item.text(0), item.checkState(0))
        assert item.checkState(0) != Qt.PartiallyChecked, f"unexpect PartiallyChecked({item.text()})"
        tag_state = True if item.checkState(0) == Qt.Checked else False
        tag = item.data(0, Qt.UserRole)

        tag_system = self.parent().tag_system
        paths = self._get_cur_focus_paths()
        assert len(paths)!=0, "slotItemCheckStateChanged but len of paths is zero"
        for path in paths:
            tagSet = tag_system.getTag(path)
            if tag_state and tag not in tagSet:
                tagSet[tag] = None
            elif not tag_state and tag in tagSet:
                tagSet.pop(tag)
            tag_system.updateTag(path, tagSet)
        
        self.saveBtn.setEnabled(True)
        self.resetBtn.setEnabled(True)

    def slotSave(self):
        self.parent().tag_system.save()
        self.saveBtn.setEnabled(False)
        self.resetBtn.setEnabled(False)

    def slotReset(self):
        result = QMessageBox.question(self, '重设', '你确定要重设吗？')
        if result != QMessageBox.Yes:
            return

        self.parent().tag_system.reset()
        
        self.remake_tree()
        
        self.saveBtn.setEnabled(False)
        self.resetBtn.setEnabled(False)

    def slotMenuPopup(self, pos):
        item = self.tagTree.itemAt(pos)
        if item is None:
            self.removeTagAction.setEnabled(False)
        else:
            self.removeTagAction.setEnabled(True)
        action = self.menu.exec_(self.tagTree.mapToGlobal(pos))


        if action is self.addTagAction:
            self.slotAddMetaTag(item)
        elif action is self.removeTagAction:
            self.slotRemoveMetaTag(item)

    def slotAddMetaTag(self, fatherItem):
        ok,newTagName = self.execAddMetaTagDialog()
        if not ok or newTagName == "":
            return

        if fatherItem is None:
            newTag = self.parent().tag_system.addMetaTag(newTagName, 0)
            newItem = TagTreeItem()
            self.tagTree.addTopLevelItem(newItem)
        else:
            newTag = self.parent().tag_system.addMetaTag(newTagName, fatherItem.data(0, Qt.UserRole))
            newItem = TagTreeItem(fatherItem)
        newItem.setCheckState(0, Qt.Unchecked)
        newItem.setData(0, Qt.UserRole, newTag)
        newItem.setText(0, newTagName)
        self.tag2item[newTag] = newItem

        self.fill_value()
        self.saveBtn.setEnabled(True)
        self.resetBtn.setEnabled(True)
        self.printInfo()

    def slotRemoveMetaTag(self, item):
        result = QMessageBox.question(self, '删除标签', f'你确定删除标签（{item.text(0)}）吗？')
        if result != QMessageBox.Yes:
            return

        tag = item.data(0, Qt.UserRole)
        self.parent().tag_system.removeMetaTag(tag)
        self.tag2item.pop(tag)
        fatherItem = item.parent()
        if fatherItem is None:
            self.tagTree.takeTopLevelItem(self.tagTree.indexOfTopLevelItem(item))
        else:
            fatherItem.removeChild(item)

        self.saveBtn.setEnabled(True)
        self.resetBtn.setEnabled(True)
        self.printInfo()

    def slotMoveMetaTag(self, item, fa_item, bro_item):
        tag = item.data(0, Qt.UserRole)
        fa_tag = fa_item.data(0, Qt.UserRole) if fa_item is not None else 0
        bro_tag = bro_item.data(0, Qt.UserRole) if bro_item is not None else -1
        self.parent().tag_system.moveMetaTag(tag, fa_tag, bro_tag)

        self.saveBtn.setEnabled(True)
        self.resetBtn.setEnabled(True)
        self.printInfo()

    def execAddMetaTagDialog(self):
        dialog = QInputDialog()
        dialog.setWindowTitle('添加标签')
        dialog.setLabelText('请输入新标签')
        dialog.setOkButtonText('确定')
        dialog.setCancelButtonText('取消')
        ret = dialog.exec_()
        return ret,dialog.textValue()

    def remake_tree(self):
        tag_system = self.parent().tag_system

        def dfs(cur_node, deep):
            for son_node in cur_node[1]:
                if deep == 0:
                    son_item = TagTreeItem()
                    self.tagTree.addTopLevelItem(son_item)
                else:
                    son_item = TagTreeItem(self.tag2item[cur_node[0]])
                son_item.setCheckState(0, Qt.Unchecked)
                son_item.setData(0, Qt.UserRole, son_node[0])
                son_item.setText(0, tag_system.meta_tag2name[son_node[0]])
                self.tag2item[son_node[0]] = son_item
                dfs(son_node, deep+1)

        self.tag2item = {}
        self.tagTree.clear()
        dfs(tag_system.meta_tag_tree, 0)
        self.fill_value()

    def fill_value(self):
        self.tagTree.push_close_signal()

        paths = self._get_cur_focus_paths()
        if paths is None:
            self._set_checkbox_disabled()
            self.tagTree.pop_signal()
            return

        tag_system = self.parent().tag_system
        path2set = {path:tag_system.getTag(path) for path in paths}

        for tag,item in self.tag2item.items():
            result = set()
            for path,tagSet in path2set.items():
                result.add(tag in tagSet)
            assert len(result) in [1,2], f'unexpect len of result({result})'
            if len(result) == 2:
                item.setCheckState(0, Qt.PartiallyChecked)
            elif len(result) == 1:
                if result.pop():
                    item.setCheckState(0, Qt.Checked)
                else:
                    item.setCheckState(0, Qt.Unchecked)

        self.tagTree.pop_signal()

    def printInfo(self):
        print(self.tag2item.keys())
        if self.parent().global_args['debug']:
            self.parent().tag_system.printMetaTagTree()

    def _get_cur_focus_paths(self):
        cur_focus = self.parent().viewWidget.cur_focus
        img_paths = [g.path for g in cur_focus if g.filetype=='img']
        if len(cur_focus) != len(img_paths):
            return None
        if len(img_paths) == 0:
            return None
        return img_paths

    def _set_checkbox_disabled(self):
        for tag in self.tag2item:
            self.tag2item[tag].setData(0, Qt.CheckStateRole, None)

    
class TagTreeItem(QTreeWidgetItem):
    def setData(self, column, role, value):
        is_check_changed = self.treeWidget().is_signal_open() and \
                           column==0 and \
                           role==Qt.CheckStateRole and \
                           self.data(column, role) is not None and \
                           self.checkState(0)!=value
        ret = super().setData(column, role, value)
        if is_check_changed:
            self.treeWidget().itemCheckStateChanged.emit(self)
        return ret

class TagTree(QTreeWidget):
    itemCheckStateChanged = pyqtSignal(TagTreeItem)

    def __init__(self, tagView):
        super().__init__()

        self.tagView = tagView

        self.signal_stack = [True]
        self.enter_items = []

        self.setHeaderHidden(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            item = self.itemAt(e.pos())
            fa_item,bro_item = self._get_fa_and_bro_item(item)
            self.enter_items = [item,fa_item,bro_item]

        return super().mousePressEvent(e)

    def dropEvent(self, e):
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
        self.signal_stack.pop(-1)

    def push_close_signal(self):
        self.signal_stack.append(False)

    def is_signal_open(self):
        return self.signal_stack[-1]

    def _get_fa_and_bro_item(self, item):
        if item is None:
            fa_item = bro_item = None
        else:
            fa_item = item.parent()
            if fa_item is None:
                bro_item = self.topLevelItem(self.indexOfTopLevelItem(item)-1)
            else:
                bro_item = fa_item.child(fa_item.indexOfChild(item)-1)
        return fa_item,bro_item
