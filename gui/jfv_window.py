import os,sys
from warnings import filterwarnings

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from img_system import ImgSystem
from tag_system import TagSystem
from gui.view_widget import ViewWidget,GridWidget
from gui.filter_widget import FilterWidget

class JFVWindow(QMainWindow):
    tinyImgReady = pyqtSignal(int,int,str)
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
                                   self.global_args['tinyimg_filedir'])
        self.tag_system = TagSystem(self.global_args['tag_filepath'],
                                   self.global_args['img_extnames'])

        self.createAction()
        self.createMenu()
        self.createBody()

        self.tinyImgReady.connect(self.slotTinyImgLoaded)
        self.imgReady.connect(self.slotImgLoaded)

    def createAction(self):
        self.aboutAction = QAction('版本信息', self)
        self.aboutAction.triggered.connect(self.slotAboutAction)

    def createMenu(self):
        self.helpMenu = self.menuBar().addMenu('帮助')
        self.helpMenu.addAction(self.aboutAction)

    def createBody(self):
        self.statusLabel = QLabel()
        self.statusBar().addWidget(self.statusLabel)

        self.viewWidget = ViewWidget(self)
        self.setCentralWidget(self.viewWidget)

        self.filterWidget = FilterWidget('筛选工作区', self)
        self.addDockWidget(Qt.TopDockWidgetArea, self.filterWidget)

    def loadImg(self, widget, path):
        if self.img_system.hasImg(path):
            img = self.img_system.getImg(path)
            widget.imgLabel.setPixmap(img)
        else:
            def fx():
                self.imgReady.emit(path)
            self.img_system.getImg_async(path, fx)

    def loadTinyImg(self, grid, path):
        if self.img_system.hasTinyImg(path):
            img = self.img_system.getTinyImg(path)
            grid.imgLabel.setPixmap(img)
        else:
            def fx():
                self.tinyImgReady.emit(?, ?, path)
            self.img_system.getTinyImg_async(path, fx)

    def slotFilterImgs(self):
        pathStr = self.filterWidget.pathLineEdit.text()
        tagStr = self.filterWidget.tagLineEdit.text()
        if pathStr == "":
            pathStr = self.global_args['img_default_filedir']
            self.filterWidget.pathLineEdit.setText(self.global_args['img_default_filedir'])
        if tagStr != "":
            select_imgs = self.tag_system.filterImage(pathStr, tagStr)
            self.viewWidget.showImgs(select_imgs)
        else:
            self.viewWidget.showDir(pathStr)

    def slotTinyImgLoaded(self, grid, path):
        img = self.img_system.getTinyImg(path)
        grid.imgLabel.setPixmap(img)

    def slotImgLoaded(self, path):
        img = self.img_system.getImg(path)
        self.viewWidget.

    def slotAboutAction(self):
        msgbox = QMessageBox()
        msgbox.setWindowTitle('版本信息')
        msgbox.setText('N0.1')
        msgbox.exec_()
