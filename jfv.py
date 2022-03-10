import os,sys

import yaml
from PyQt5.QtWidgets import QApplication

from gui.jfv_window import JFVWindow

class JFV(object):
    def __init__(self):
        self.global_args = yaml.load(open('global.yml',encoding='utf-8'), yaml.FullLoader)
        
        self.app = QApplication([])
        self.gui = JFVWindow(self.global_args)

    def start(self):
        self.gui.show()
        self.app.exec_()

    def close(self):
        self.gui.img_system.close()

if __name__ == '__main__':
    try:
        jfv = JFV()
        jfv.start()
        jfv.close()
    except:
        jfv.close()
        raise
        