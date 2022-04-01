import os,sys
import threading
import subprocess

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import win32api
import win32con

from img_system import ImgSystem
from tag_system import TagSystem
from gui.view_widget import ViewWidget
from gui.filter_widget import FilterWidget
from gui.tag_widget import TagWidget
from gui.info_widget import InfoWidget
from gui.fastfunc_widget import FastFuncWidget

'''
JFVWindow为GUI顶层类，也统领其他模块（图片系统和标签系统）。
所有GUI子类都会引用JFVWindow，因此它们是整个GUI系统的一部分，不能独立使用。

GUI界面结构
    JFVWindow
    |-FilterWidget      筛选工作区
    |-ViewWidget        中心显示区
    |-TagWidget         标签树
    |-InfoWidget        图片信息区
    |-FastFuncWidget    快速功能区
    |
    |-TagSystem         标签系统模块（负责标签管理）
    |-ImgSystem         图片系统模块（负责图片异步读取、缩略图、缓存管理）

信号与槽结构
    1. 理论上，所有子界面的信号都是发射到JFVWindow的槽上，再处理和调用子界面的假槽或函数
    2. 但有一些信号，跟其他子界面无关，则只发射到子界面的槽上，避免JFVWindow槽函数过多
    3. 也有子界面的信号，先发射到自己的槽上处理，再往上调用JFVWindow的假槽
    4. 事件函数充当信号的角色，调用槽函数

主要的两类更新界面操作
    1. 通过改变filterWidget来刷新页面的。一般先修改filterWidget，然后调用slotFilterOK
    2. 不涉及filterWidget的。一般包括viewWidget的各种模式切换和更新，和其他子界面的更新。
viewWidget的更新
    第一类更新主要有两类：
        1. _showDir() （目录模式，显示目录的所有文件）
        2. _showImgs() （筛选模式，显示筛选结果）
    第二类更新包括了：
        1. _showImg() （图片模式，显示大图）
        2. 鼠标点击，键盘点击等
        它们会影响焦点grid，进而迫使其他子界面更新
viewWidget以外的子界面更新比较单一，包括：
    1. TagWidget.fill_value()
    2. InfoWidget.fill_value()
    3. FastFuncWidget.update_history() (只出现在改变filterWidget的第一类操作)
'''

class JFVWindow(QMainWindow):
    #图片系统的callback信号
    tinyImgReady = pyqtSignal(str,int,int,int)
    imgReady = pyqtSignal(str) 

    def __init__(self, global_args):
        super().__init__()
        # 处理全局参数
        self.global_args = global_args
        require_abs_args = ['tag_filedir','tinyimg_filedir','dir_icon_path',
                            'file_icon_path','img_icon_path','fastfunc_filepath']
        for name in require_abs_args:
            self.global_args[name] = os.path.join(os.getcwd(), self.global_args[name]) #参数里的路径换成绝对路径

        # 初始化文件系统
        os.makedirs(os.path.join(os.getcwd(),'data'), exist_ok=True)

        # 载入资源
        self.res = {}
        self.res['dir_icon'] = QPixmap(self.global_args['dir_icon_path'])
        self.res['file_icon'] = QPixmap(self.global_args['file_icon_path'])
        self.res['img_icon'] = QPixmap(self.global_args['img_icon_path'])

        # 创建其他模块
        self.img_system = ImgSystem(self.global_args['img_poolsize'],
                                   self.global_args['tinyimg_poolsize'],
                                   self.global_args['img_extnames'],
                                   self.global_args['tinyimg_filedir'],
                                   self)
        self.tag_system = TagSystem(self.global_args['tag_filedir'],
                                   self.global_args['img_extnames'])

        # 创建GUI界面
        self.createAction()
        self.createMenu()
        self.createToolBar()
        self.createBody()

        # GUI信号
        self.tinyImgReady.connect(self.slotTinyImgLoaded)
        self.imgReady.connect(self.slotImgLoaded)

        # 初始化界面
        self.slotFilterOK()

    def createAction(self):
        '''
        创建Action
        '''
        self.aboutAction = QAction('版本信息', self)
        self.aboutAction.triggered.connect(self.slotAboutAction)
        self.backAction = QAction('后退', self)
        self.backAction.triggered.connect(self.slotBackAction)
        self.homeAction = QAction('主页', self)
        self.homeAction.triggered.connect(self.slotHomeAction)
        self.helpAction = QAction('帮助', self)
        self.helpAction.triggered.connect(self.slotHelpAction)
        self.optionsAction = QAction('首选项', self)
        self.optionsAction.triggered.connect(self.slotOptionsAction)
        self.tagCntAction = QAction('标签统计', self)
        self.tagCntAction.triggered.connect(self.slotTagCntAction)
        self.tagCurPageCntAction = QAction('当前页面标签统计', self)
        self.tagCurPageCntAction.triggered.connect(self.slotTagCurPageCntAction)
        self.tagTransferAction = QAction('标签迁移', self)
        self.tagTransferAction.triggered.connect(self.slotTagTransferAction)

    def createMenu(self):
        '''
        创建菜单Menu
        '''
        self.funcMenu = self.menuBar().addMenu('功能')
        self.funcMenu.addAction(self.tagCntAction)
        self.funcMenu.addAction(self.tagCurPageCntAction)
        self.funcMenu.addAction(self.tagTransferAction)
        self.helpMenu = self.menuBar().addMenu('帮助')
        self.helpMenu.addAction(self.aboutAction)
        self.helpMenu.addAction(self.helpAction)
        self.helpMenu.addAction(self.optionsAction)

    def createToolBar(self):
        '''
        创建工具栏
        '''
        self.toolBar = self.addToolBar('all')
        self.toolBar.addAction(self.backAction)
        self.toolBar.addAction(self.homeAction)

    def createBody(self):
        '''
        创建主体
        '''
        # 自身
        self.setWindowTitle('Jpg Viewing and Filtering')
        # 状态栏
        self.statusLabel = QLabel()
        self.statusBar().addWidget(self.statusLabel)
        # 子级界面
        self.viewWidget = ViewWidget(self)
        self.setCentralWidget(self.viewWidget)

        self.filterWidget = FilterWidget('筛选工作区', self)
        self.addDockWidget(Qt.TopDockWidgetArea, self.filterWidget)

        self.tagWidget = TagWidget('标签树', self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.tagWidget)

        self.infoWidget = InfoWidget('图片信息', self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.infoWidget)

        self.fastFuncWidget = FastFuncWidget('快速功能区', self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.fastFuncWidget)

        # dockwidget设定
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)

    def loadImg(self, path):
        '''
        桥接viewWidget和tag_system函数
        viewWidget的imgWidget通过调用它来加载图片
        
        args
            path: str 图片路径
        '''
        if self.img_system.hasImg(path):
            # 图片有缓存则马上设置
            img = self.img_system.getImg(path)
            self.viewWidget.imgWidget.setImg(img)
        else:
            # 否则，先考虑加载缩略图，再异步加载原图
            if self.img_system.hasTinyImg(path):
                tinyimg = self.img_system.getTinyImg(path)
                self.viewWidget.imgWidget.setImg(tinyimg)
            self.img_system.getImg_async(path, None)

    def loadTinyImg(self, grid, path):
        '''
        桥接viewWidget和tag_system函数
        viewWidget通过调用它来加载缩略图
        
        args
            grid: GridWidget 要设置缩略图的缩略图格子
            path: str 图片路径
        '''
        if self.img_system.hasTinyImg(path):
            # 缩略图有缓存则马上设置
            img = self.img_system.getTinyImg(path)
            grid.imgLabel.setPixmap(img)
        else:
            # 否则，异步加载缩略图
            self.img_system.getTinyImg_async(path, (grid.pos[0],grid.pos[1],self.viewWidget.cur_cnt))

    def setStatusInfo(self, s):
        '''
        设置状态栏的文字
        args
            s:str 要设置的文字
        '''
        self.statusLabel.setText(s)

    def slotTinyImgLoaded(self, path, x, y, cnt):
        '''
        缩略图异步加载完毕，响应tinyImgReady的槽
        args
            path: str 异步加载的缩略图路径
            x,y: int 设置缩略图的gridWidget在整个网格的坐标
            cnt: int 异步加载前，viewWidget的计数器的值
        '''
        # 判断viewWidget是否已刷新页面，刷新了则无需再加载
        if cnt != self.viewWidget.cur_cnt:
            return
        grid = self.viewWidget.gridLayout.itemAtPosition(x, y).widget() #由于槽不能传GUI类，因此用x,y来获取grid
        img = self.img_system.getTinyImg(path)
        grid.imgLabel.setPixmap(img)

    def slotImgLoaded(self, path):
        '''
        图片异步加载完毕，响应imgReady的槽
        args
            path: str 异步加载的图片路径
        '''
        # 判断viewWidget的imgWidget是否已显示了别的图片
        if path != self.viewWidget.imgWidget.cur_path:
            return
        
        img = self.img_system.getImg(path)
        self.viewWidget.imgWidget.setImg(img)

    def slotFilterOK(self):
        '''
        [第一类更新界面操作]
        根据filterWidget的路径和标签筛选信息，更新所有子页面
        是filterWidget的确认按钮的槽，同时也会被其他需要刷新页面的函数调用
        这些函数通常先修改filterWidget的lineEdit，然后调用该函数刷新页面
        '''
        # 取出路径和标签筛选信息
        pathStr = self.filterWidget.pathLineEdit.text().strip()
        tagStr = self.filterWidget.tagLineEdit.text().strip()
        # 路径为空，则当成是主页
        if pathStr == "":
            pathStr = self.global_args['img_default_filedir']
            self.filterWidget.pathLineEdit.setText(self.global_args['img_default_filedir'])
        if tagStr != "":
            # 标签筛选信息不为空，则进入筛选模式
            select_imgs = self.tag_system.filterImage(pathStr, tagStr)
            self.viewWidget._showImgs(select_imgs)
        else:
            # 否则，进入目录模式
            self.viewWidget._showDir(pathStr)
        # 更新其他相关子界面
        self.tagWidget.fill_value() #标签树更新（应该是更新成非法）
        self.infoWidget.fill_value() #图片信息更新（应该是更新成非法）
        self.fastFuncWidget.updateHistory(pathStr, tagStr) #更新路径和标签筛选历史

    def slotGridPress(self, grid):
        '''
        [第二类更新界面操作]
        gridWidget鼠标按下事件的槽函数（目前没区分鼠标左右键）
        更新viewWidget的焦点grid，以及更新其他子界面
        args
            grid: GridWidget 被点击的缩略图格子
        '''
        # 获取ctrl和shift键有没有按下（这会影响焦点grid的计算）
        ctrl = win32api.GetKeyState(win32con.VK_CONTROL) < 0
        shift = win32api.GetKeyState(win32con.VK_SHIFT) < 0
        # 调用子界面函数处理和更新
        self.viewWidget.slotGridPress(grid, ctrl, shift)
        self.tagWidget.fill_value()
        self.infoWidget.fill_value()

    def slotGridDoubleClick(self, grid):
        '''
        [两类更新界面操作都有]
        gridWidget鼠标双击事件（以及grid右键菜单打开）的槽函数（目前没区分鼠标左右键）
        根据grid的类型进行三种处理
        args
            grid: GridWidget 被点击的缩略图格子
        '''
        if grid.filetype == 'file':
            # 文件，则提示不能打开
            msgbox = QMessageBox()
            msgbox.setWindowTitle('提示')
            msgbox.setText('JFV只能打开图片')
            msgbox.exec_()
        elif grid.filetype == 'dir':
            # 目录，则打开目录
            self.filterWidget.pathLineEdit.setText(grid.path)
            self.slotFilterOK()
        elif grid.filetype == 'img':
            # 图片，则viewWidget切换到图片模式
            self.viewWidget._showImg(grid)
            self.tagWidget.fill_value()
            self.infoWidget.fill_value()
        else:
            assert False, f'not expected type:{grid.filetype}'

    def slotImgDoubleClick(self):
        '''
        [第二类更新界面操作]
        imgWidget鼠标双击时间的槽函数（目前没区分鼠标左右键）
        让viewWidget从图片模式切换回目录模式/筛选模式，并更新其他子界面
        '''
        self.viewWidget.slotImgDoubleClick()
        self.tagWidget.fill_value()
        self.infoWidget.fill_value()

    def slotListDoubleClick(self, item):
        '''
        [第一类更新界面操作]
        fastFuncWidget里的item被点击后的槽
        将点击的item的路径/标签筛选串应用到filterWidget，进而更新界面
        args
            item: ListWidgetItem 被点击的路径/标签筛选串对应的GUI项
        '''
        k = item.listWidget().k1 #确认是path还是tag
        s = item.text()
        if k == 'path':
            self.filterWidget.pathLineEdit.setText(s)
        else:
            self.filterWidget.tagLineEdit.setText(s)
        self.slotFilterOK()

    def slotImgKeyPress(self, e):
        '''
        [第二类更新界面操作]
        viewWidget的imgWidget键盘点击事件的槽
        图片模式下，左右切换
        args
            e: QKeyEvent 事件信息
        '''
        self.viewWidget.slotImgKeyPress(e)
        self.tagWidget.fill_value()
        self.infoWidget.fill_value()

    def slotAboutAction(self):
        '''
        aboutAction的槽。
        显示版本信息
        '''
        msgbox = QMessageBox()
        msgbox.setWindowTitle('版本信息')
        msgbox.setText('v-1.1')
        msgbox.exec_()

    def slotBackAction(self):
        '''
        [第一类更新界面操作]
        backAction的槽。
        '''
        if self.filterWidget.tagLineEdit.text().strip() != "":
            # 如果有标签筛选串，则该后退操作为删除筛选串
            self.filterWidget.tagLineEdit.setText('')
        else:
            # 否则，则是普通的路径后退操作
            cur_path = self.filterWidget.pathLineEdit.text().strip()
            base_path,_ = os.path.split(cur_path)
            self.filterWidget.pathLineEdit.setText(base_path)
        self.slotFilterOK()

    def slotHomeAction(self):
        '''
        [第一类更新界面操作]
        homeAction的槽。
        回到首页，并去除筛选。
        '''
        self.filterWidget.pathLineEdit.setText(self.global_args['img_default_filedir'])
        self.filterWidget.tagLineEdit.setText('')
        self.slotFilterOK()

    def slotHelpAction(self):
        '''
        helpAction的槽。
        显示帮助信息。
        '''
        msgbox = QMessageBox()
        msgbox.setWindowTitle('帮助')
        msgbox.setText('自己思考')
        msgbox.exec_()

    def slotOptionsAction(self):
        '''
        optionsAction的槽。
        打开全局参数文件。
        '''
        subprocess.Popen(f'notepad {os.path.join(os.getcwd(),"global.yml")}')

    def slotTagCntAction(self):
        '''
        tagCntAction的槽。
        打开标签统计消息框。
        '''
        cur_path = self.filterWidget.pathLineEdit.text().strip()

        # 创建GUI树
        tree = QTreeWidget()
        header = QTreeWidgetItem()
        header.setText(0, '标签')
        header.setText(1, '数量')
        header.setText(2, '子树总数')
        tree.setHeaderItem(header)

        tag2item = {}

        def dfs(cur_node, deep, fa_item):
            # 统计数量
            tag = cur_node[0]
            cur_cnt = self.tag_system.calc_tag_cnt(cur_path, tag)
            # 构建item
            if deep == 0:
                item = QTreeWidgetItem()
                tree.addTopLevelItem(item)
            else:
                item = QTreeWidgetItem(fa_item)
            item.setText(0, self.tag_system.getTagName(tag))
            item.setText(1, str(cur_cnt))
            tag2item[tag] = item
            # dfs儿子
            son_cnts = []
            for son_node in cur_node[1]:
                son_cnt = dfs(son_node, deep+1, item)
                son_cnts.append(son_cnt)
            # 统计自己
            sum_son_cnt = sum(son_cnts)
            if len(cur_node[1]) != 0:
                item.setText(2, str(cur_cnt+sum_son_cnt))
            # 儿子上色
            if len(cur_node[1]) != 0:
                max_son_cnt = max(son_cnts)
                if max_son_cnt>0 and not any([len(son_node[1])>0 for son_node in cur_node[1]]):
                    for ix,son_node in enumerate(cur_node[1]):
                        son_item = tag2item[son_node[0]]
                        k1 = son_cnts[ix]/max_son_cnt
                        k2 = -(son_cnts[ix]/max_son_cnt-1)**2 + 1
                        k = k2
                        son_item.setForeground(1, QColor(round(k*255),0,0))
            return cur_cnt+sum_son_cnt
        
        dfs(self.tag_system.meta_tag_tree, 0, None)
        tree.expandAll()
        tree.setMinimumSize(400,400)
        tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)

        # 创建消息窗口
        msgbox = QDialog()
        msgbox.setWindowTitle('标签统计')
        layout = QVBoxLayout(msgbox)
        layout.addWidget(QLabel(f'路径: {cur_path}'))
        layout.addWidget(tree)
        msgbox.exec_()

    def slotTagCurPageCntAction(self):
        '''
        tagCurPageCntAction的槽。(目前照搬tagCntAction修改)
        打开当前页面标签统计消息框。
        与标签统计的区别是，它是统计当前viewWidget的所有grid，而标签统计是统计某目录下的所有子孙图片
        '''
        cur_path = self.filterWidget.pathLineEdit.text().strip()
        cur_tagstr = self.filterWidget.tagLineEdit.text().strip()

        # 创建GUI树
        tree = QTreeWidget()
        header = QTreeWidgetItem()
        header.setText(0, '标签')
        header.setText(1, '数量')
        header.setText(2, '子树总数')
        tree.setHeaderItem(header)

        tag2item = {}

        def calc_tag_cnt(tag):
            cnt = 0
            for i in range(self.viewWidget.gridLayout.count()):
                grid = self.viewWidget.gridLayout.itemAt(i).widget()
                if grid.filetype != 'img':
                    continue
                tagSet = self.tag_system.getTag(grid.path)
                if tag in tagSet:
                    cnt += 1
            return cnt

        def dfs(cur_node, deep, fa_item):
            # 统计数量
            tag = cur_node[0]
            cur_cnt = calc_tag_cnt(tag)
            # 构建item
            if deep == 0:
                item = QTreeWidgetItem()
                tree.addTopLevelItem(item)
            else:
                item = QTreeWidgetItem(fa_item)
            item.setText(0, self.tag_system.getTagName(tag))
            item.setText(1, str(cur_cnt))
            tag2item[tag] = item
            # dfs儿子
            son_cnts = []
            for son_node in cur_node[1]:
                son_cnt = dfs(son_node, deep+1, item)
                son_cnts.append(son_cnt)
            # 统计自己
            sum_son_cnt = sum(son_cnts)
            if len(cur_node[1]) != 0:
                item.setText(2, str(cur_cnt+sum_son_cnt))
            # 儿子上色
            if len(cur_node[1]) != 0:
                max_son_cnt = max(son_cnts)
                if max_son_cnt>0 and not any([len(son_node[1])>0 for son_node in cur_node[1]]):
                    for ix,son_node in enumerate(cur_node[1]):
                        son_item = tag2item[son_node[0]]
                        k1 = son_cnts[ix]/max_son_cnt
                        k2 = -(son_cnts[ix]/max_son_cnt-1)**2 + 1
                        k = k2
                        son_item.setForeground(1, QColor(round(k*255),0,0))
            return cur_cnt+sum_son_cnt
        
        dfs(self.tag_system.meta_tag_tree, 0, None)
        tree.expandAll()
        tree.setMinimumSize(400,400)
        tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)

        # 创建消息窗口
        msgbox = QDialog()
        msgbox.setWindowTitle('当前页面标签统计')
        layout = QVBoxLayout(msgbox)
        layout.addWidget(QLabel(f'路径: {cur_path}'))
        layout.addWidget(QLabel(f'标签: {cur_tagstr}'))
        layout.addWidget(tree)
        msgbox.exec_()

    def slotTagTransferAction(self):
        '''
        tagTransferAction的槽。
        实现标签转移。
        '''
        # 核心部件
        srcLineEdit = QLineEdit()
        dstLineEdit = QLineEdit()
        srcLineEdit.setText(r'D:\OneDrive\照片') #默认
        dstLineEdit.setText(r'D:\照片') #默认
        okBtn = QPushButton('确定')
        cancelBtn = QPushButton('取消')
        # 布局
        msgbox = QDialog()
        msgbox.setWindowTitle('标签迁移')
        g_layout = QGridLayout()
        g_layout.addWidget(QLabel('原始目录路径'), 0, 0)
        g_layout.addWidget(srcLineEdit, 0, 1)
        g_layout.addWidget(QLabel('目标目录路径'), 1, 0)
        g_layout.addWidget(dstLineEdit, 1, 1)
        hbox = QHBoxLayout()
        hbox.addWidget(okBtn)
        hbox.addWidget(cancelBtn)
        layout = QVBoxLayout(msgbox)
        layout.addLayout(g_layout)
        layout.addLayout(hbox)
        # 按钮的槽
        def slotOK():
            msgbox.accept()
        
        def slotCancel():
            msgbox.reject()
        
        okBtn.clicked.connect(slotOK)
        cancelBtn.clicked.connect(slotCancel)

        # 展示对话框
        ret = msgbox.exec_()

        # 核心系统执行
        if ret == QDialog.Accepted:
            srcPath = srcLineEdit.text().strip()
            dstPath = dstLineEdit.text().strip()
            num = self.tag_system.transfer_dir(srcPath, dstPath)

            QMessageBox.information(self, '标签迁移', f'迁移成功（{num}项）')

    def closeEvent(self, e):
        '''
        关闭事件
        关闭之前先检查tag是否未保存，未保存则提示是否保存
        '''
        if not self.tag_system.is_dirty:
            return super().closeEvent(e)

        msg = QMessageBox()
        msg.setText('你的标签修改还未保存！')
        msg.addButton('保存再退出', QMessageBox.AcceptRole)
        msg.addButton('直接退出', QMessageBox.RejectRole)
        msg.addButton('取消', QMessageBox.DestructiveRole)
        result = msg.exec_()

        if result == QMessageBox.AcceptRole:
            self.tag_system.save()
            return super().closeEvent(e)
        elif result == QMessageBox.RejectRole:
            return super().closeEvent(e)
        elif result == QMessageBox.DestructiveRole:
            e.ignore()
