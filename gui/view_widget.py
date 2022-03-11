from fileinput import filename
from genericpath import isdir
import os
from posixpath import dirname

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class ViewWidget(QStackedWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.col = 2
        self.cur_cnt = 0
        self.cur_focus = []

        self.dirWidget = QScrollArea()
        self.dirWidget.setWidgetResizable(True)
        self.contentWidget = QWidget()
        self.gridLayout = QGridLayout(self.contentWidget)
        self.gridLayout.addWidget(GridWidget(self.parent(), r'D:\照片', (0,0)), 0, 0)
        self.dirWidget.setWidget(self.contentWidget)

        self.imgWidget = ImgWidget(self.parent())

        self.addWidget(self.dirWidget)
        self.addWidget(self.imgWidget)


    def slotGridPress(self, grid, ctrl, shift):
        if not ctrl and not shift:
            for g in self.cur_focus:
                g.lose_focus()
            self.cur_focus = [grid]
            grid.get_focus()
        elif ctrl and not shift:
            if grid in self.cur_focus:
                grid.lose_focus()
                self.cur_focus.remove(grid)
            else:
                grid.get_focus()
                self.cur_focus.append(grid)
        elif not ctrl and shift:
            for g in self.cur_focus:
                g.lose_focus()
            if len(self.cur_focus) == 0:
                last_grid = self.gridLayout.itemAtPosition(0,0).widget()
            else:
                last_grid = self.cur_focus[-1]
            self.cur_focus = []
            if grid.pos[0] < last_grid.pos[0] or grid.pos[0]==last_grid.pos[0] and grid.pos[1]<=last_grid.pos[1]:
                pbeg,pend = grid.pos,last_grid.pos
            else:
                pbeg,pend = last_grid.pos,grid.pos
            pcur = list(pbeg)
            while True:
                cur_grid = self.gridLayout.itemAtPosition(*pcur).widget()
                cur_grid.get_focus()
                self.cur_focus.append(cur_grid)
                
                if tuple(pcur) == pend:
                    break
                
                pcur[1] += 1
                if pcur[1] == self.col:
                    pcur[0] += 1
                    pcur[1] = 0
            if pbeg != grid.pos:
                self.cur_focus = self.cur_focus[::-1]
        elif ctrl and shift:
            if len(self.cur_focus) == 0:
                last_grid = self.gridLayout.itemAtPosition(0,0).widget()
            else:
                last_grid = self.cur_focus[-1]
            if grid.pos[0] < last_grid.pos[0] or grid.pos[0]==last_grid.pos[0] and grid.pos[1]<=last_grid.pos[1]:
                pbeg,pend = grid.pos,last_grid.pos
            else:
                pbeg,pend = last_grid.pos,grid.pos
            pcur = list(pbeg)
            while True:
                cur_grid = self.gridLayout.itemAtPosition(*pcur).widget()
                if cur_grid not in self.cur_focus:
                    cur_grid.get_focus()
                    self.cur_focus.append(cur_grid)
                
                if tuple(pcur) == pend:
                    break
                
                pcur[1] += 1
                if pcur[1] == self.col:
                    pcur[0] += 1
                    pcur[1] = 0
            if pbeg != grid.pos:
                self.cur_focus = self.cur_focus[::-1]

    def slotImgDoubleClick(self):
        self.setCurrentWidget(self.dirWidget)

    def _showDir(self, path):
        names = ['..'] + os.listdir(path)
        paths = [os.path.abspath(os.path.join(path,k)) for k in names]
        dir_paths = [k for k in paths if os.path.isdir(k)]
        file_paths = [k for k in paths if os.path.isfile(k)]

        self.setCurrentWidget(self.dirWidget)
        self._clearGrids()
        self._addGrids(dir_paths+file_paths)

    def _showImgs(self, paths):
        self.setCurrentWidget(self.dirWidget)
        self._clearGrids()
        self._addGrids(paths)

    def _showImg(self, grid):
        self.setCurrentWidget(self.imgWidget)
        self.imgWidget.reset_img(grid.path)
        for g in self.cur_focus:
            g.lose_focus()
        grid.get_focus()
        self.cur_focus = [grid]

    def _clearGrids(self):
        for i in range(self.gridLayout.count()):
            self.gridLayout.itemAt(i).widget().deleteLater()
        self.cur_cnt += 1
        self.cur_focus = []

    def _addGrids(self, paths):
        pos = [0,0]
        for i,path in enumerate(paths):
            if i == 0 and os.path.isdir(path):
                grid = GridWidget(self.parent(), path, tuple(pos), last_dir=True)
            else:    
                grid = GridWidget(self.parent(), path, tuple(pos))
            self.gridLayout.addWidget(grid, pos[0], pos[1])
            pos[1] += 1
            if pos[1] == self.col:
                pos[0] += 1
                pos[1] = 0


class GridWidget(QWidget):
    def __init__(self, mainWindow, path, pos, last_dir=False):
        super().__init__()
        self.mainWindow = mainWindow
        self.path = path
        self.pos = pos

        # self.setFixedSize(300,250)

        if last_dir:
            self.name = '..'
        else:
            _,self.name = os.path.split(self.path)

        if os.path.isdir(self.path):
            self.filetype = 'dir'
        elif os.path.splitext(self.path)[1] in self.mainWindow.global_args['img_extnames']:
            self.filetype = 'img'
        else:
            self.filetype = 'file'

        self.imgLabel = QLabel('图片')
        self.imgLabel.setFixedSize(250,250)
        self.nameLabel = QLabel(self.name)
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

    def get_pre_grid(self):
        x,y = self.pos
        y -= 1
        if y == -1:
            x -= 1
            y = 0
        return self.mainWindow.viewWidget.gridLayout.itemAtPosition(x, y).widget()

    def get_next_grid(self):
        x,y = self.pos
        y += 1
        if y == self.mainWindow.viewWidget.col:
            x += 1
            y = 0
        return self.mainWindow.viewWidget.gridLayout.itemAtPosition(x, y).widget()

    def get_focus(self):
        palette = QPalette()
        palette.setColor(QPalette.WindowText, Qt.red)
        self.nameLabel.setPalette(palette)

    def lose_focus(self):
        palette = QPalette()
        palette.setColor(QPalette.WindowText, Qt.black)
        self.nameLabel.setPalette(palette)

    def mouseDoubleClickEvent(self, e):
        self.mainWindow.slotGridDoubleClick(self)

    def mousePressEvent(self, e):
        self.mainWindow.slotGridPress(self)



class ImgWidget(QWidget):
    def __init__(self, mainWindow, path=None):
        super().__init__()

        self.mainWindow = mainWindow
        self.cur_path = path

        self.imgLabel = QLabel()
        self.imgLabel.setFixedSize(800, 800)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.imgLabel)

        self.cur_path = "D:\\照片\\尬\\IMG_20211226_120802.jpg"
        self.reset_img(self.cur_path)

    def reset_img(self, path):
        self.cur_path = path
        if self.cur_path is None:
            self.imgLabel.setText('')
        else:
            self.mainWindow.loadImg(self.cur_path)

    def setImg(self, img):
        img = img.scaled(800, 800)
        self.imgLabel.setPixmap(img)

    def mouseDoubleClickEvent(self, e):
        self.mainWindow.slotImgDoubleClick()
