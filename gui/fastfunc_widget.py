import os,sys

import pickle
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class FastFuncWidget(QDockWidget):
    def __init__(self, title, parent):
        super().__init__(title, parent)

        self.widgets = {'path':{},'tag':{}}
        for i in ['path','tag']:
            for j in ['history','favour']:
                self.widgets[i][j] = MyListWidget(self.parent(), i, j)

        self.content = QWidget()
        layout = QVBoxLayout(self.content)
        layout.addWidget(self.widgets['path']['history'])
        layout.addWidget(self.widgets['tag']['history'])
        layout.addWidget(self.widgets['path']['favour'])
        layout.addWidget(self.widgets['tag']['favour'])
        self.setWidget(self.content)

        self.loadData()

    def loadData(self):
        path = self.parent().global_args['fastfunc_filepath']
        if not os.path.exists(path):
            self.saveData()
            return
        data = pickle.load(open(path, 'rb'))
        for i in ['path','tag']:
            for j in ['history','favour']:
                self.widgets[i][j].loadData(data[i][j])

    def saveData(self):
        data = {'path':{},'tag':{}}
        for i in ['path','tag']:
            for j in ['history','favour']:
                data[i][j] = self.widgets[i][j].dumpData()
        pickle.dump(data, open(self.parent().global_args['fastfunc_filepath'], 'wb'))

    def updateHistory(self, pathStr, tagStr):
        self.widgets['path']['history'].updateHistory(pathStr)
        self.widgets['tag']['history'].updateHistory(tagStr)

class MyListWidget(QListWidget):
    def __init__(self, mainWindow, k1, k2):
        super().__init__()
        self.mainWindow = mainWindow
        self.k1 = k1
        self.k2 = k2

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.slotMenuPopup)

        self.itemDoubleClicked.connect(self.mainWindow.slotListDoubleClick)

    def slotMenuPopup(self, pos):
        item = self.itemAt(pos)
        menu = QMenu()
        addFavourAction = QAction('添加到收藏夹')
        removeFavourAction = QAction('从收藏夹删除')
        clearHistoryAction = QAction('清空历史')
        if self.k2 == 'history':
            if item is not None:
                menu.addAction(addFavourAction)
            menu.addAction(clearHistoryAction)
        else:
            if item is not None:
                menu.addAction(removeFavourAction)
            else:
                return

        action = menu.exec_(self.mapToGlobal(pos))

        if action is addFavourAction:
            self.slotAddFavour(item)
        elif action is removeFavourAction:
            self.slotRemoveFavour(item)
        elif action is clearHistoryAction:
            self.slotClearHistory()

    def slotAddFavour(self, item):
        lw = self.mainWindow.fastFuncWidget.widgets[self.k1]['favour']
        s = item.text()
        if lw.hasStr(s):
            return
        newItem = QListWidgetItem()
        newItem.setText(s)
        lw.addItem(newItem)
        self.mainWindow.fastFuncWidget.saveData()

    def slotRemoveFavour(self, item):
        self.takeItem(self.row(item))

    def slotClearHistory(self):
        self.clear()

    def updateHistory(self, s):
        if s == "":
            return
        if self.hasStr(s):
            self.removeItemByStr(s)
        item = QListWidgetItem()
        item.setText(s)
        self.insertItem(0, item)
        if self.count() > self.mainWindow.global_args['max_history_size']:
            self.takeItem(self.count()-1)

    def hasStr(self, s):
        for i in range(self.count()):
            item = self.item(i)
            if item.text() == s:
                return True
        return False
    
    def removeItemByStr(self, s):
        for i in range(self.count()):
            item = self.item(i)
            if item.text() == s:
                self.takeItem(self.row(item))
                return True
        return False

    def loadData(self, data):
        self.clear()
        for i in range(len(data)):
            item = QListWidgetItem()
            item.setText(data[i])
            self.addItem(item)

    def dumpData(self):
        data = []
        for i in range(self.count()):
            item = self.item(i)
            data.append(item.text())
        return data