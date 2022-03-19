import os,sys

import exifread
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

'''
InfoWidget
|-imgInfoWidget 
|-fileInfoWidget（未实现）
|-tagInfoWidget（未实现）
(它们理论上是个list，但QTreeWidget能提供表头和多列)
'''

class InfoWidget(QDockWidget):
    def __init__(self, title, parent):
        super().__init__(title, parent)
        # 创建图片信息列表
        self.imgInfoWidget = QTreeWidget()
        self.imgInfoWidget.setColumnCount(2)
        self.imgInfoWidget.setHeaderHidden(True)
        # 设置列表中的item
        self.imgInfoItems = []
        names = ['焦距','光圈','快门','ISO']
        for i in range(4):
            item = QTreeWidgetItem()
            item.setText(0, names[i])
            self.imgInfoItems.append(item)
        self.imgInfoWidget.addTopLevelItems(self.imgInfoItems)    
        # 布局
        self.content = QWidget()
        layout = QVBoxLayout(self.content)
        layout.addWidget(self.imgInfoWidget)
        self.setWidget(self.content)
    
    def fill_value(self):
        '''
        更新界面
        （目前只有img_info实装了）    
        '''
        self.fill_img_info()

    def fill_img_info(self):
        '''
        更新imgInfo
        '''
        # 判断焦点合法和获取图片信息
        img_paths = self._get_cur_focus_paths()
        if img_paths is not None and len(img_paths)==1:
            vals = self._get_img_info(img_paths[0])
        else:
            vals = [None,None,None,None]
        # 设置GUI信息
        for i in range(4):
            if vals[i] is None:
                vals[i] = ""
        for i in range(4):
            self.imgInfoItems[i].setText(1, vals[i])

    def _get_cur_focus_paths(self):
        '''
        获取当前viewWidget的所有焦点grid的路径
        有下列情况时，均返回None表示焦点非法：
        1. 焦点含有非图片文件
        2. 没有焦点
        ret
            [str]|None 焦点grid的路径列表
        '''
        cur_focus = self.parent().viewWidget.cur_focus
        img_paths = [g.path for g in cur_focus if g.filetype=='img']
        if len(cur_focus) != len(img_paths):
            return None
        if len(img_paths) == 0:
            return None
        return img_paths


    def _get_img_info(self, path):
        '''
        获取图片信息
        args
            path:str 图片路径
        ret
            [str,str,str,str] 焦段，光圈，快门，ISO
        '''
        # 获取文件的图片信息
        file = open(path, 'rb')
        tags = exifread.process_file(file)
        names = [
            'EXIF FocalLength','EXIF FNumber',
            'EXIF ExposureTime','EXIF ISOSpeedRatings',
        ]
        vals = [None,None,None,None]
        for i in range(4):
            name = names[i]
            if name in tags:
                vals[i] = tags[name].printable
        #图片信息加工
        if vals[0] is not None:
            if '/' in vals[0]:
                a,b = list(map(int,vals[0].split('/')))
                f = a/b
                if f < 10:
                    f = f"{f:.1f}"
                    f = f.replace('.0', '')
                else:
                    f = str(round(f))
            else:
                f = vals[0]
            vals[0] = f"{f}mm"
        if vals[1] is not None:
            if '/' in vals[1]:
                a,b = list(map(int,vals[1].split('/')))
                aper = a/b
                if aper < 1:
                    aper = f"{aper:.2f}"
                else:
                    aper = f"{aper:.1f}"
            else:
                aper = vals[1]
            vals[1] = f"F{aper}"
        if vals[2] is not None:
            vals[2] = f"{vals[2]}s"
        return vals
