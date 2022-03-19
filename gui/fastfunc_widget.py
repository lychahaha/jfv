import os,sys

import pickle
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

'''
FastFuncWidget
|-pathHistoryList 路径历史列表
|-tagHistoryList 标签历史列表
|-pathFavourList 路径收藏夹列表
|-tagFavourList 标签收藏夹列表
|
|-（四个列表都会套一个GroupBox来突出标题）

该Widget的作用包括三个：
1. 记录历史（包括路径和标签筛选串）
2. 收藏夹功能（同上）
3. 快速访问（双击ListItem时会将其路径/标签筛选串信息设置到FilterWidget，然后更新页面）
'''

class FastFuncWidget(QDockWidget):
    def __init__(self, title, parent):
        super().__init__(title, parent)
        # 创建列表GUI
        self.widgets = {'path':{},'tag':{}}
        for i in ['path','tag']:
            for j in ['history','favour']:
                self.widgets[i][j] = MyListWidget(self.parent(), i, j)
        # 布局
        self.content = QWidget()
        layout = QVBoxLayout(self.content)
        layout.addWidget(MyGroupBox(self.widgets['path']['history'],'路径历史'))
        layout.addWidget(MyGroupBox(self.widgets['tag']['history'],'标签历史'))
        layout.addWidget(MyGroupBox(self.widgets['path']['favour'],'路径收藏夹'))
        layout.addWidget(MyGroupBox(self.widgets['tag']['favour'],'标签收藏夹'))
        self.setWidget(self.content)
        # 加载数据
        self.loadData()

    def loadData(self):
        '''
        加载数据到GUI列表里
        '''
        path = self.parent().global_args['fastfunc_filepath']
        if not os.path.exists(path): #第一次没有文件的话会创建文件
            self.saveData()
            return
        # 加载数据到GUI列表里
        data = pickle.load(open(path, 'rb'))
        for i in ['path','tag']:
            for j in ['history','favour']:
                self.widgets[i][j].loadData(data[i][j])

    def saveData(self):
        '''
        保存GUI列表里的数据到文件上
        '''
        data = {'path':{},'tag':{}}
        for i in ['path','tag']:
            for j in ['history','favour']:
                data[i][j] = self.widgets[i][j].dumpData()
        pickle.dump(data, open(self.parent().global_args['fastfunc_filepath'], 'wb'))

    def updateHistory(self, pathStr, tagStr):
        '''
        更新历史，包括路径和标签筛选串
        '''
        self.widgets['path']['history'].updateHistory(pathStr)
        self.widgets['tag']['history'].updateHistory(tagStr)

class MyListWidget(QListWidget):
    def __init__(self, mainWindow, k1, k2):
        super().__init__()
        self.mainWindow = mainWindow
        self.k1 = k1
        self.k2 = k2
    
        self.setContextMenuPolicy(Qt.CustomContextMenu) #激活右键菜单
        self.customContextMenuRequested.connect(self.slotMenuPopup) #设置右键菜单信号连接

        self.itemDoubleClicked.connect(self.mainWindow.slotListDoubleClick) #设置双击信号连接

    def slotMenuPopup(self, pos):
        '''
        右键菜单的槽
        args
            pos: Qsize 右键点击的位置
        '''
        # 创建和设置菜单
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
        # 执行
        action = menu.exec_(self.mapToGlobal(pos))
        # 根据点击的项执行命令
        if action is addFavourAction:
            self.slotAddFavour(item)
        elif action is removeFavourAction:
            self.slotRemoveFavour(item)
        elif action is clearHistoryAction:
            self.slotClearHistory()

    def slotAddFavour(self, item):
        '''
        右键菜单添加收藏夹的假槽
        args
            item:QListWidgetItem 要添加收藏夹的item
        '''
        lw = self.mainWindow.fastFuncWidget.widgets[self.k1]['favour']
        s = item.text()
        if lw.hasStr(s):
            return
        newItem = QListWidgetItem()
        newItem.setText(s)
        lw.addItem(newItem)
        self.mainWindow.fastFuncWidget.saveData()

    def slotRemoveFavour(self, item):
        '''
        右键菜单从收藏夹删除的假槽
        args
            item:QListWidgetItem 要从收藏夹删除的item
        '''
        self.takeItem(self.row(item))

    def slotClearHistory(self):
        '''
        右键菜单清空历史的假槽
        '''
        self.clear()

    def updateHistory(self, s):
        '''
        更新访问历史
        args
            s: 更新页面时的路径/标签筛选串
        '''
        # 特判空串
        if s == "":
            return
        # 如果已有，则先删除再添加
        if self.hasStr(s):
            self.removeItemByStr(s)
        # 添加新item
        item = QListWidgetItem()
        item.setText(s)
        self.insertItem(0, item)
        # 历史已满时，删除最旧的
        if self.count() > self.mainWindow.global_args['max_history_size']:
            self.takeItem(self.count()-1)

    def hasStr(self, s):
        '''
        判断该列表是否包含某路径/标签筛选串
        args
            s:str 路径/标签筛选串
        '''
        for i in range(self.count()):
            item = self.item(i)
            if item.text() == s:
                return True
        return False
    
    def removeItemByStr(self, s):
        '''
        删除该列表中对应某路径/标签筛选串的item
        args
            s:str 路径/标签筛选串
        ret
            bool 是否删除了
        '''
        for i in range(self.count()):
            item = self.item(i)
            if item.text() == s:
                self.takeItem(self.row(item))
                return True
        return False

    def loadData(self, data):
        '''
        载入数据
        args
            data:[str] 数据
        '''
        self.clear() #先清空GUI列表
        for i in range(len(data)):
            item = QListWidgetItem()
            item.setText(data[i])
            self.addItem(item)

    def dumpData(self):
        '''
        析出数据
        ret
            data:[str] 数据
        '''
        data = []
        for i in range(self.count()):
            item = self.item(i)
            data.append(item.text())
        return data

class MyGroupBox(QGroupBox):
    '''
    重写是为了设置Title等样式，省事
    '''
    def __init__(self, content, title):
        super().__init__()
        self.setTitle(title)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(content)
