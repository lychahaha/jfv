from fileinput import filename
import os
from posixpath import dirname

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class ViewWidget(QStackedWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.col = 2
        self.cur_pos = [0,0]
        self.cur_path = self.parent().global_args['img_default_filedir']
        self.cur_cnt = 0
        self.show_mode = 'dir' # dir|filter

        self.dirWidget = QScrollArea()
        self.gridLayout = QGridLayout(self.dirWidget)

        self.imgWidget = ImgWidget(self.parent())

        self.addWidget(self.dirWidget)
        self.addWidget(self.imgWidget)

        self.showDir(self.cur_path)

    def showImgs(self, paths):
        self.show_mode = 'filter'

    def showDir(self, path):
        self.clearLayout()

        names = ['..'] + os.listdir(path)
        dir_names = [k for k in names if os.path.isdir(os.path.join(path,k))]
        file_names = [k for k in names if not os.path.isdir(os.path.join(path,k))]
        for name in dir_names:
            self._addGrid(path,name)
        for name in file_names:
            self._addGrid(path,name)

        self.show_mode = 'dir'
        self.cur_path = path

    def clearLayout(self):
        for i in range(self.gridLayout.count()):
            self.gridLayout.itemAt(i).widget().deleteLater()
        self.cur_pos = [0,0]
        self.cur_cnt += 1

    def _addGrid(self, dir_path, name):
        path = os.path.abspath(os.path.join(dir_path,name))
        if os.path.isdir(path):
            grid = GridWidget(self.parent(), 'dir', path, name)
        elif os.path.splitext(path)[1] in self.parent().global_args['img_extnames']:
            grid = GridWidget(self.parent(), 'img', path, name)
        else:
            grid = GridWidget(self.parent(), 'file', path, name)
        self.gridLayout.addWidget(grid, self.cur_pos[0], self.cur_pos[1])
        self._addPos()

    def _addPos(self):
        x,y = self.cur_pos
        y += 1
        if y == self.col:
            x += 1
            y = 0
        self.cur_pos = [x,y]

    def _subPos(self):
        x,y = self.cur_pos
        y -= 1
        if y == -1:
            x -= 1
            y = self.col - 1
        self.cur_pos = [x,y]


class GridWidget(QWidget):
    def __init__(self, mainWindow, filetype, path, name):
        super().__init__()
        self.mainWindow = mainWindow
        self.filetype = filetype
        self.path = path
        self.name = name

        self.imgLabel = QLabel('图片')
        self.nameLabel = QLabel(name)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.imgLabel)
        self.layout.addWidget(self.nameLabel)

        if self.filetype == 'dir':
            self.imgLabel.setPixmap(self.mainWindow.res['dir_icon'])
        elif self.filetype == 'file':
            self.imgLabel.setPixmap(self.mainWindow.res['file_icon'])
        elif self.filetype == 'img':
            self.mainWindow.loadTinyImg(self, self.path)
        else:
            assert False, f'not expected type:{self.filetype}'

class ImgWidget(QWidget):
    def __init__(self, mainWindow, path=None):
        super().__init__()

        self.mainWindow = mainWindow
        self.cur_path = path

        self.imgLabel = QLabel()
        self.reset_img()

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.imgLabel)

    def reset_img(self):
        if self.cur_path is None:
            self.imgLabel.setText('')
        else:
            self.mainWindow.loadImg(self, self.cur_path)
