import os,sys

import exifread
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class InfoWidget(QDockWidget):
    def __init__(self, title, parent):
        super().__init__(title, parent)

        self.imgInfoWidget = QTreeWidget()
        self.imgInfoWidget.setColumnCount(2)
        self.imgInfoWidget.setHeaderHidden(True)

        self.imgInfoItems = []
        names = ['焦距','光圈','快门','ISO']
        for i in range(4):
            item = QTreeWidgetItem()
            item.setText(0, names[i])
            self.imgInfoItems.append(item)
        self.imgInfoWidget.addTopLevelItems(self.imgInfoItems)    

        self.content = QWidget()
        layout = QVBoxLayout(self.content)
        layout.addWidget(self.imgInfoWidget)
        self.setWidget(self.content)
    
    def fill_value(self):
        self.fill_img_info()

    def fill_img_info(self):
        img_paths = self._get_cur_focus_paths()
        if img_paths is not None and len(img_paths)==1:
            vals = self._get_img_info(img_paths[0])
        else:
            vals = [None,None,None,None]
        
        for i in range(4):
            if vals[i] is None:
                vals[i] = ""
        for i in range(4):
            self.imgInfoItems[i].setText(1, vals[i])

    def _get_cur_focus_paths(self):
        cur_focus = self.parent().viewWidget.cur_focus
        img_paths = [g.path for g in cur_focus if g.filetype=='img']
        if len(cur_focus) != len(img_paths):
            return None
        if len(img_paths) == 0:
            return None
        return img_paths


    def _get_img_info(self, path):
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
