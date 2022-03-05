from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class InfoWidget(QDockWidget):
    def __init__(self, title, parent):
        super().__init__(title, parent)

        self.pathLineEdit = QLineEdit()
        self.tagLineEdit = QLineEdit()
        self.pathClearBtn = QPushButton('清除')
        self.tagClearBtn = QPushButton('清除')
        self.okBtn = QPushButton('确定')

        self.content = QWidget()
        self.layout = QGridLayout(self.content)
        self.layout.addWidget(QLabel('路径'), 0, 0)
        self.layout.addWidget(self.pathLineEdit, 0, 1)
        self.layout.addWidget(self.pathClearBtn, 0, 2)
        self.layout.addWidget(QLabel('标签'), 1, 0)
        self.layout.addWidget(self.tagLineEdit, 1, 1)
        self.layout.addWidget(self.tagClearBtn, 1, 2)
        self.layout.addWidget(self.okBtn, 2, 0)
        self.setWidget(self.content)
        