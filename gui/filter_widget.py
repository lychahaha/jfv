from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

'''
FilterWidget
|-pathLineEdit 路径编辑器
|-tagLineEdit 标签编辑器
|-pathClearBtn 路径清除按钮
|-tagClearBtn 标签清除按钮
|-okBtn 确认按钮
|-onlyCurDirCBox 是否只筛选当前目录
'''

class FilterWidget(QDockWidget):
    def __init__(self, title, parent):
        super().__init__(title, parent)

        self.pathLineEdit = QLineEdit()
        self.pathLineEdit.setText(self.parent().global_args['img_default_filedir']) #设置默认路径
        self.tagLineEdit = QLineEdit()
        self.pathClearBtn = QPushButton('清除')
        self.tagClearBtn = QPushButton('清除')
        self.okBtn = QPushButton('确定')
        self.onlyCurDirCBox = QCheckBox('只筛选当前目录')

        self.pathLineEdit.returnPressed.connect(self.parent().slotFilterOK) #回车键触发确认
        self.tagLineEdit.returnPressed.connect(self.parent().slotFilterOK)
        self.pathClearBtn.clicked.connect(self.slotPathClear)
        self.tagClearBtn.clicked.connect(self.slotTagClear)
        self.okBtn.clicked.connect(self.parent().slotFilterOK)

        self.content = QWidget()
        self.layout = QGridLayout(self.content)
        self.layout.addWidget(QLabel('路径'), 0, 0)
        self.layout.addWidget(self.pathLineEdit, 0, 1)
        self.layout.addWidget(self.pathClearBtn, 0, 2)
        self.layout.addWidget(QLabel('标签'), 1, 0)
        self.layout.addWidget(self.tagLineEdit, 1, 1)
        self.layout.addWidget(self.tagClearBtn, 1, 2)
        self.layout.addWidget(self.okBtn, 2, 0)
        self.layout.addWidget(self.onlyCurDirCBox, 2, 1)
        self.setWidget(self.content)

        self.setTabOrder(self.pathLineEdit, self.tagLineEdit) #设置tab顺序，path编辑完tab到tag编辑
        
    def slotPathClear(self):
        '''
        点击路径清除按钮的槽
        清空路径编辑器的字符串
        '''
        self.pathLineEdit.setText('')

    def slotTagClear(self):
        '''
        点击标签清除按钮的槽
        清空标签编辑器的字符串
        '''
        self.tagLineEdit.setText('')