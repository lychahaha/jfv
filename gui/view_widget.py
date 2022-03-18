import os

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class ViewWidget(QStackedWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.col = 2
        self.cur_cnt = 0
        self.cur_focus = []

        self.dirWidget = MyScrollArea(self.parent())
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

    def slotImgKeyPress(self, e):
        assert e.key() in [Qt.Key_Left, Qt.Key_Right], f'unexpected key({e.key()})'
        is_left = e.key() == Qt.Key_Left
        old_item = self.cur_focus[0]
        old_ix = self.gridLayout.indexOf(old_item)
        new_item = self._findPreImgGrid(old_ix) if is_left else self._findNextImgGrid(old_ix)
        if new_item is None:
            return
        self._showImg(new_item)

    def printInfo(self):
        print('focus:', [os.path.split(g.path)[1] for g in self.cur_focus])
        print(f'cur_cnt:{self.cur_cnt}')
        print(f'img_path:{os.path.split(self.imgWidget.cur_path)[1]}')

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

    def _findNextImgGrid(self, ix):
        for i in range(ix+1, self.gridLayout.count()):
            item = self.gridLayout.itemAt(i).widget()
            if item.filetype == 'img':
                return item
        return None

    def _findPreImgGrid(self, ix):
        for i in range(ix-1, -1, -1):
            item = self.gridLayout.itemAt(i).widget()
            if item.filetype == 'img':
                return item
        return None


class MyScrollArea(QScrollArea):
    def __init__(self, mainWindow):
        super().__init__()
        self.mainWindow = mainWindow

    def keyPressEvent(self, e):
        return super().keyPressEvent(e)


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
        self.imgLabel.setMinimumSize(600, 600)
        self.imgLabel.setAlignment(Qt.AlignCenter)
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
        img_w,img_h = img.size().width(),img.size().height()
        screen_w,screen_h = self.size().width(),self.size().height()
        ratio_w,ratio_h = img_w/screen_w,img_h/screen_h
        ratio = max(ratio_w,ratio_h)
        new_w,new_h = round(img_w/ratio),round(img_h/ratio)
        img = img.scaled(new_w, new_h)
        self.imgLabel.setPixmap(img)

    def mouseDoubleClickEvent(self, e):
        self.mainWindow.slotImgDoubleClick()

    def keyPressEvent(self, e):
        if self.mainWindow.viewWidget.currentWidget() is self \
           and e.key() in [Qt.Key_Left,Qt.Key_Right]:
            self.mainWindow.slotImgKeyPress(e)
            return
        else:
            return super().keyPressEvent(e)

    def resizeEvent(self, e):
        if self.mainWindow.viewWidget.currentWidget() is self:
            img = self.mainWindow.loadImg(self.cur_path)
        return super().resizeEvent(e)