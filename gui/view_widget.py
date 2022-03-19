from genericpath import isdir
import os
import re
import functools

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

'''
ViewWidget
|-dirWidget
    |-GridLayout
        |-GridWidget
        |-GridWidget
        |-...
|-imgWidget

ViewWidget的三种显示模式：
1. 目录模式（显示目录的所有文件）
2. 筛选模式（显示筛选结果）
3. 图片模式（显示大图）

'''

class ViewWidget(QStackedWidget):
    def __init__(self, parent):
        super().__init__(parent)
        # 重要变量
        self.col = 2 #grid表的列数
        self.cur_cnt = 0 #页面计数器（每当刷新页面会+1，用来判断缩略图是否还要加载）
        self.cur_focus = [] #当前焦点grid列表（十分重要，其他界面都依赖它更新参数）
        # 创建GUI部件
        self.dirWidget = MyScrollArea(self.parent())
        self.dirWidget.setWidgetResizable(True) #设置这个才能动态resize
        self.contentWidget = QWidget()
        self.gridLayout = QGridLayout(self.contentWidget)
        self.dirWidget.setWidget(self.contentWidget)

        self.imgWidget = ImgWidget(self.parent())

        self.addWidget(self.dirWidget)
        self.addWidget(self.imgWidget)

    def slotGridPress(self, grid, ctrl, shift):
        '''
        grid被点击的假槽（信号先发到顶层窗口，然后顶层窗口调用该函数）
        args
            grid:GridWidget 被点击的grid
            ctrl:bool 是否按下了ctrl
            shift:bool 是否按下了shift
        '''
        if not ctrl and not shift:
            # 单纯的点击
            # 去掉之前所有焦点，点击的grid获得焦点
            for g in self.cur_focus:
                g.lose_focus()
            self.cur_focus = [grid]
            grid.get_focus()
        elif ctrl and not shift:
            # 带ctrl的点击
            # 只改变点击的grid是否在焦点列表里的状态
            if grid in self.cur_focus:
                grid.lose_focus()
                self.cur_focus.remove(grid)
            else:
                grid.get_focus()
                self.cur_focus.append(grid)
        elif not ctrl and shift:
            # 带shift的点击
            # 去掉之前所有焦点，上一次和本次的点击的grid之间的grid全部获得焦点
            # 如果是第一次点击，则假设上一次点击的是第0号grid
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
            # 同时带ctrl和shift的点击
            # 与只带shift点击的差别只在，不去掉之前的所有焦点
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
        '''
        图片双击的假槽（信号先发到顶层窗口，然后顶层窗口调用该函数）
        将显示模式从图片模式变成目录/筛选模式
        '''
        self.setCurrentWidget(self.dirWidget)

    def slotImgKeyPress(self, e):
        '''
        图片模式时键盘点击的假槽（信号先发到顶层窗口，然后顶层窗口调用该函数）
        目前只实现左右键，功能是切换上一张/下一张图片（注意要跳过文件和目录）
        如果没有上一张/下一张，则不操作
        args
            e:QKeyEvent 键盘事件
        '''
        # 计算上一张/下一张图片
        assert e.key() in [Qt.Key_Left, Qt.Key_Right], f'unexpected key({e.key()})'
        is_left = e.key() == Qt.Key_Left
        old_item = self.cur_focus[0]
        old_ix = self.gridLayout.indexOf(old_item)
        new_item = self._findPreImgGrid(old_ix) if is_left else self._findNextImgGrid(old_ix)
        # 判断和切换
        if new_item is None: #没有上一张/下一张，则不操作
            return
        self._showImg(new_item)

    def printInfo(self):
        '''
        打印相关信息（debug用）
        '''
        print('focus:', [os.path.split(g.path)[1] for g in self.cur_focus])
        print(f'cur_cnt:{self.cur_cnt}')
        print(f'img_path:{os.path.split(self.imgWidget.cur_path)[1]}')

    def _showDir(self, path):
        '''
        切换到目录模式，并显示某目录的所有文件（该函数不负责其他界面的信息更新）
        args
            path:str 目录的路径
        '''
        # 获取目录和文件列表
        names = ['..'] + os.listdir(path) #加入返回上级的目录
        paths = [os.path.abspath(os.path.join(path,k)) for k in names] #换成绝对路径
        dir_paths = [k for k in paths if os.path.isdir(k)]
        file_paths = [k for k in paths if os.path.isfile(k)]
        dir_paths = self._smartSort(dir_paths)
        file_paths = self._smartSort(file_paths)
        # 设置GUI
        self.setCurrentWidget(self.dirWidget) #切换到目录/筛选模式
        self._clearGrids() #先清空grid表格
        self._addGrids(dir_paths+file_paths) #先加目录再加文件

    def _showImgs(self, paths):
        '''
        切换到筛选模式，显示所有图片（该函数不负责其他界面的信息更新）
        args
            paths:[str] 所有筛选出来的图片的路径列表
        '''
        paths = self._smartSort(paths)
        self.setCurrentWidget(self.dirWidget)
        self._clearGrids()
        self._addGrids(paths)

    def _showImg(self, grid):
        '''
        切换到筛选模式，显示所有图片（该函数不负责其他界面的信息更新）
        args
            grid:GridWidget 要显示大图的缩略图GUI部件
        '''
        self.setCurrentWidget(self.imgWidget)
        self.imgWidget.reset_img(grid.path)
        # 要设置焦点
        for g in self.cur_focus:
            g.lose_focus()
        grid.get_focus()
        self.cur_focus = [grid]

    def _clearGrids(self):
        '''
        清空grid表格
        包括清空GUI项，和更新变量
        '''
        for i in range(self.gridLayout.count()):
            self.gridLayout.itemAt(i).widget().deleteLater()
        self.cur_cnt += 1
        self.cur_focus = []

    def _addGrids(self, paths):
        '''
        添加grid项（一次刷新只能调用一次）
        args
            paths:[str] 所有要显示的文件/图片的路径列表
        '''
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
        '''
        寻找下一个图片grid（用于图片模式时切换下一张图片）
        没有下一张时返回None
        args
            ix:int 目标在gridLayout的ix
        ret
            item:GridWidget|None 目标的下一张图片对应的缩略图grid
        '''
        for i in range(ix+1, self.gridLayout.count()):
            item = self.gridLayout.itemAt(i).widget()
            if item.filetype == 'img':
                return item
        return None

    def _findPreImgGrid(self, ix):
        '''
        寻找上一个图片grid（用于图片模式时切换上一张图片）
        没有上一张时返回None
        args
            ix:int 目标在gridLayout的ix
        ret
            item:GridWidget|None 目标的上一张图片对应的缩略图grid
        '''
        for i in range(ix-1, -1, -1):
            item = self.gridLayout.itemAt(i).widget()
            if item.filetype == 'img':
                return item
        return None

    def _smartSort(self, paths):
        '''
        智能排序
        如果文件名字都是带规律的序号，那么按序号排序，而不是字典序
        args:
            paths:[str] 文件路径列表
        ret
            ret_paths:[str] 排序后的文件路径列表
        '''
        def cmp(s1,s2):
            ibeg = 0
            while ibeg < min(len(s1),len(s2)):
                if s1[ibeg] != s2[ibeg]:
                    break
                ibeg += 1
            if ibeg == min(len(s1),len(s2)):
                if len(s1) == len(s2):
                    return 0
                if ibeg == len(s1):
                    return -1
                else:
                    return 1

            if not s1[ibeg].isdecimal() or not s2[ibeg].isdecimal():
                if s1[ibeg] < s2[ibeg]:
                    return -1
                else:
                    return 1
            else:
                def find_num(s, ibeg):
                    while ibeg < len(s):
                        if not s[ibeg].isdecimal():
                            break
                        ibeg += 1
                    return ibeg
                def find_pre_num(s, ibeg):
                    while ibeg > -1:
                        if not s[ibeg].isdecimal():
                            break
                        ibeg -= 1
                    return ibeg + 1
                ibeg = find_pre_num(s1, ibeg)
                iend1 = find_num(s1, ibeg)
                iend2 = find_num(s2, ibeg)
                f1 = float(s1[ibeg:iend1])
                f2 = float(s2[ibeg:iend2])
                if f1 < f2:
                    return -1
                else:
                    return 1

        return sorted(paths, key=functools.cmp_to_key(cmp))

class MyScrollArea(QScrollArea):
    '''
    目录/筛选模式时，实现键盘方向键要用到(未实现)
    '''
    def __init__(self, mainWindow):
        super().__init__()
        self.mainWindow = mainWindow

    def keyPressEvent(self, e):
        return super().keyPressEvent(e)


class GridWidget(QWidget):
    def __init__(self, mainWindow, path, pos, last_dir=False):
        super().__init__()
        self.mainWindow = mainWindow #顶层窗口
        self.path = path #当前grid代表的图片路径
        self.pos = pos #当前grid所在的gridLayout的坐标

        # self.setFixedSize(300,250)

        # 特判上一级目录的名字
        if last_dir:
            self.name = '..'
        else:
            _,self.name = os.path.split(self.path)
        # 当前grid的文件类型
        if os.path.isdir(self.path):
            self.filetype = 'dir'
        elif os.path.splitext(self.path)[1] in self.mainWindow.global_args['img_extnames']:
            self.filetype = 'img'
        else:
            self.filetype = 'file'
        # 设置GUI项
        self.imgLabel = QLabel('图片')
        self.imgLabel.setFixedSize(250,250)
        self.nameLabel = QLabel(self.name)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.imgLabel)
        self.layout.addWidget(self.nameLabel)
        # 设置显示的图片
        if self.filetype == 'dir':
            self.imgLabel.setPixmap(self.mainWindow.res['dir_icon'])
        elif self.filetype == 'file':
            self.imgLabel.setPixmap(self.mainWindow.res['file_icon'])
        elif self.filetype == 'img':
            self.mainWindow.loadTinyImg(self, self.path)
        else:
            assert False, f'not expected type:{self.filetype}'

    def get_focus(self):
        '''
        获得焦点（只设置GUI样式）
        '''
        palette = QPalette()
        palette.setColor(QPalette.WindowText, Qt.red)
        self.nameLabel.setPalette(palette)

    def lose_focus(self):
        '''
        失去焦点（只设置GUI样式）
        '''
        palette = QPalette()
        palette.setColor(QPalette.WindowText, Qt.black)
        self.nameLabel.setPalette(palette)

    def mouseDoubleClickEvent(self, e):
        '''
        双击事件，调用顶层窗口的假槽
        '''
        self.mainWindow.slotGridDoubleClick(self)

    def mousePressEvent(self, e):
        '''
        点击事件，调用顶层窗口的假槽
        '''
        self.mainWindow.slotGridPress(self)


class ImgWidget(QWidget):
    def __init__(self, mainWindow, path=None):
        super().__init__()

        self.mainWindow = mainWindow #顶层窗口
        self.cur_path = path #当前显示图片的路径
        # 设置GUI
        self.imgLabel = QLabel()
        self.imgLabel.setMinimumSize(600, 600)
        self.imgLabel.setAlignment(Qt.AlignCenter) #居中
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.imgLabel)
        # 没有下面会有bug（原因未知）
        self.cur_path = "D:\\照片\\尬\\IMG_20211226_120802.jpg"
        self.reset_img(self.cur_path)

    def reset_img(self, path):
        '''
        设置图片
        它会调用顶层窗口的函数来异步/同步获取图片，最后通过setImg真正设置
        整条调用路径是：
            1. reset_img（设置路径）
            2. JFVWindow.loadImg（桥接GUI与ImgSystem）
            3. ImgSystem.getImg/getImg_async（获取/加载图片）
            4. JFVWindow.slotImgLoaded（异步回调）
            5. setImg（GUI设置）
        args
            path:str 图片路径
        '''
        self.cur_path = path
        if self.cur_path is None:
            self.imgLabel.setText('')
        else:
            self.mainWindow.loadImg(self.cur_path)

    def setImg(self, img):
        '''
        reset_img的最后一步
        先resize成最大的大小，再设置
        args
            img:QPixmap 图片
        '''
        img_w,img_h = img.size().width(),img.size().height()
        screen_w,screen_h = self.size().width(),self.size().height()
        ratio_w,ratio_h = img_w/screen_w,img_h/screen_h
        ratio = max(ratio_w,ratio_h)
        new_w,new_h = round(img_w/ratio),round(img_h/ratio)
        img = img.scaled(new_w, new_h)
        self.imgLabel.setPixmap(img)

    def mouseDoubleClickEvent(self, e):
        '''
        双击事件
        调用顶层窗口的假槽处理
        '''
        self.mainWindow.slotImgDoubleClick()

    def keyPressEvent(self, e):
        '''
        键盘点击事件
        先判断合法性，再调用顶层窗口的假槽处理
        '''
        if self.mainWindow.viewWidget.currentWidget() is self \
           and e.key() in [Qt.Key_Left,Qt.Key_Right]:
            self.mainWindow.slotImgKeyPress(e)
            return
        else:
            return super().keyPressEvent(e)

    def resizeEvent(self, e):
        '''
        resize事件，重新载入
        args
            e:QEvent
        '''
        if self.mainWindow.viewWidget.currentWidget() is self:
            self.mainWindow.loadImg(self.cur_path)
        return super().resizeEvent(e)