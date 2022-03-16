import os,sys
import threading

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

class JFVWindow(QMainWindow):
    tinyImgReady = pyqtSignal(str,int,int,int)
    imgReady = pyqtSignal(str)

    def __init__(self, global_args):
        super().__init__()
        self.global_args = global_args
        require_abs_args = ['tag_filepath','tinyimg_filedir','dir_icon_path',
                            'file_icon_path','img_icon_path']
        for name in require_abs_args:
            self.global_args[name] = os.path.join(os.getcwd(), self.global_args[name])

        os.makedirs(os.path.join(os.getcwd(),'data'), exist_ok=True)

        self.res = {}
        self.res['dir_icon'] = QPixmap(self.global_args['dir_icon_path'])
        self.res['file_icon'] = QPixmap(self.global_args['file_icon_path'])
        self.res['img_icon'] = QPixmap(self.global_args['img_icon_path'])

        self.img_system = ImgSystem(self.global_args['img_poolsize'],
                                   self.global_args['tinyimg_poolsize'],
                                   self.global_args['img_extnames'],
                                   self.global_args['tinyimg_filedir'],
                                   self)
        self.tag_system = TagSystem(self.global_args['tag_filepath'],
                                   self.global_args['img_extnames'])

        self.createAction()
        self.createMenu()
        self.createToolBar()
        self.createBody()

        self.tinyImgReady.connect(self.slotTinyImgLoaded)
        self.imgReady.connect(self.slotImgLoaded)

        self.slotFilterOK()

    def createAction(self):
        self.aboutAction = QAction('版本信息', self)
        self.aboutAction.triggered.connect(self.slotAboutAction)
        self.backAction = QAction('后退', self)
        self.backAction.triggered.connect(self.slotBackAction)
        self.homeAction = QAction('主页', self)
        self.homeAction.triggered.connect(self.slotHomeAction)
        self.helpAction = QAction('帮助', self)
        self.helpAction.triggered.connect(self.slotHelpAction)
        self.favourAction = QAction('收藏', self)
        self.favourAction.triggered.connect(self.slotFavourAction)

    def createMenu(self):
        self.helpMenu = self.menuBar().addMenu('帮助')
        self.helpMenu.addAction(self.aboutAction)
        self.helpMenu.addAction(self.helpAction)

    def createToolBar(self):
        self.toolBar = self.addToolBar('all')
        self.toolBar.addAction(self.backAction)
        self.toolBar.addAction(self.homeAction)
        self.toolBar.addAction(self.favourAction)

    def createBody(self):
        self.statusLabel = QLabel()
        self.statusBar().addWidget(self.statusLabel)

        self.viewWidget = ViewWidget(self)
        self.setCentralWidget(self.viewWidget)

        self.filterWidget = FilterWidget('筛选工作区', self)
        self.addDockWidget(Qt.TopDockWidgetArea, self.filterWidget)

        self.tagWidget = TagWidget('标签树', self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.tagWidget)

        self.infoWidget = InfoWidget('图片信息', self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.infoWidget)

    def loadImg(self, path):
        if self.img_system.hasImg(path):
            img = self.img_system.getImg(path)
            self.viewWidget.imgWidget.setImg(img)
        else:
            if self.img_system.hasTinyImg(path):
                tinyimg = self.img_system.getTinyImg(path)
                self.viewWidget.imgWidget.setImg(tinyimg)
            self.img_system.getImg_async(path, None)

    def loadTinyImg(self, grid, path):
        if self.img_system.hasTinyImg(path):
            img = self.img_system.getTinyImg(path)
            print("k0:"+path)
            grid.imgLabel.setPixmap(img)
        else:
            print("k:"+path)
            self.img_system.getTinyImg_async(path, (grid.pos[0],grid.pos[1],self.viewWidget.cur_cnt))

    def slotTinyImgLoaded(self, path, x, y, cnt):
        if cnt != self.viewWidget.cur_cnt:
            return
        grid = self.viewWidget.gridLayout.itemAtPosition(x, y).widget()
        img = self.img_system.getTinyImg(path)
        grid.imgLabel.setPixmap(img)

    def slotImgLoaded(self, path):
        if path != self.viewWidget.imgWidget.cur_path:
            return
        
        img = self.img_system.getImg(path)
        self.viewWidget.imgWidget.setImg(img)

    def slotFilterOK(self):
        pathStr = self.filterWidget.pathLineEdit.text().strip()
        tagStr = self.filterWidget.tagLineEdit.text().strip()
        if pathStr == "":
            pathStr = self.global_args['img_default_filedir']
            self.filterWidget.pathLineEdit.setText(self.global_args['img_default_filedir'])
        if tagStr != "":
            select_imgs = self.tag_system.filterImage(pathStr, tagStr)
            self.viewWidget._showImgs(select_imgs)
        else:
            self.viewWidget._showDir(pathStr)
        self.tagWidget.fill_value()
        self.infoWidget.fill_value()

    def slotGridPress(self, grid):
        ctrl = win32api.GetKeyState(win32con.VK_CONTROL) < 0
        shift = win32api.GetKeyState(win32con.VK_SHIFT) < 0
        self.viewWidget.slotGridPress(grid, ctrl, shift)
        self.tagWidget.fill_value()
        self.infoWidget.fill_value()

    def slotGridDoubleClick(self, grid):
        if grid.filetype == 'file':
            msgbox = QMessageBox()
            msgbox.setText('JFV只能打开图片')
            msgbox.exec_()
        elif grid.filetype == 'dir':
            self.viewWidget._showDir(grid.path)
            self.filterWidget.pathLineEdit.setText(grid.path)
            self.tagWidget.fill_value()
            self.infoWidget.fill_value()
        elif grid.filetype == 'img':
            self.viewWidget._showImg(grid)
            self.tagWidget.fill_value()
            self.infoWidget.fill_value()
        else:
            assert False, f'not expected type:{grid.filetype}'

    def slotImgDoubleClick(self):
        self.viewWidget.slotImgDoubleClick()
        self.tagWidget.fill_value()
        self.infoWidget.fill_value()

    def slotAboutAction(self):
        msgbox = QMessageBox()
        msgbox.setWindowTitle('版本信息')
        msgbox.setText('V-0.1')
        msgbox.exec_()

    def slotBackAction(self):
        cur_path = self.filterWidget.pathLineEdit.text().strip()
        base_path,_ = os.path.split(cur_path)
        self.filterWidget.pathLineEdit.setText(base_path)
        self.slotFilterOK()

    def slotHomeAction(self):
        self.filterWidget.pathLineEdit.setText(self.global_args['img_default_filedir'])
        self.filterWidget.tagLineEdit.setText('')
        self.slotFilterOK()

    def slotHelpAction(self):
        msgbox = QMessageBox()
        msgbox.setWindowTitle('帮助')
        msgbox.setText('自己思考')
        msgbox.exec_()


    def slotFavourAction(self):
        pass

