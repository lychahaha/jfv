import os
import io
import collections
import threading
import multiprocessing
from hashlib import md5
import pickle

from PIL import Image
from PIL import ImageQt
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QThread

'''
ImgSystem模块已经尽量独立于Qt/GUI使用，但由于线程队列不能传递GUI对象，因此需要传入GUI顶层窗口帮助传递参数

ImgSystem模块管理的图片包括原图和缩略图两大类

类图
ImgSystem
|-ImgReadThread 用于异步读取图片的线程
|-TinyImgReadThread 用于异步读取缩略图的线程
|
|-CachedPool 用于缓存的核心数据结构

缓存结构
    图片只有一级缓存结构（内存），缩略图有两极缓存结构（内存，硬盘）
    缩略图的缓存：
    1. 该模块会将同一目录的所有图片加载，生成缩略图，并一同保存成一个文件存入电脑
    2. 异步获取时，模块文件将加载到内存后，是以二进制串存放缩略图，而不是数字格式
    3. 同步获取时，模块会将二进制串的图片解码成QPixmap，供GUI使用
'''

class ImgSystem(object):
    def __init__(self, img_poolsize, tinyimg_poolsize, img_extnames, tinyimg_filedir, mainWindow):
        self.img_poolsize = img_poolsize #int 图片缓存池的大小
        self.tinyimg_poolsize = tinyimg_poolsize #int 缩略图缓存池的大小
        self.img_extnames = img_extnames #[str] 图片后缀列表
        self.tinyimg_filedir = tinyimg_filedir #str 保存缩略图的目录路径
        self.mainWindow = mainWindow #JFVWindow GUI顶层窗口

        # 初始化文件系统
        os.makedirs(self.tinyimg_filedir, exist_ok=True)

        # 创建缓存池
        self.img_pool = CachedPool(self.img_poolsize)
        self.tinyimg_pool = CachedPool(self.tinyimg_poolsize)

        # 创建与线程通信的消息队列
        self.img_queue = multiprocessing.Queue()
        self.tinyimg_queue = multiprocessing.Queue()

        # 创建线程
        self.p_img = ImgReadThread(self)
        self.p_tinyimg = TinyImgReadThread(self)

        # 启动线程
        self.p_img.start()
        self.p_tinyimg.start()

    def getImg(self, path):
        '''
        获取图片（同步方式）
        args
            path: str 图片路径
        ret
            QPixmap 目标图片
        '''
        return self.decodeImg(self.img_pool.get(path))

    def getTinyImg(self, path):
        '''
        获取缩略图（同步方式）
        args
            path: str 缩略图路径
        ret
            QPixmap 目标缩略图
        '''
        return self.decodeImg(self.tinyimg_pool.get(path))

    def hasImg(self, path):
        '''
        判断缓存池是否包含该图片
        args
            path: str 图片路径
        ret
            bool 是否包含
        '''
        return self.img_pool.has(path)

    def hasTinyImg(self, path):
        '''
        判断缓存池是否包含该缩略图
        args
            path: str 缩略图路径
        ret
            bool 是否包含
        '''
        return self.tinyimg_pool.has(path)

    def getImg_async(self, path, args, quickly=False):
        '''
        获取图片（异步方式）
        载入后线程会向主线程发信号
        args
            path: str 图片路径
            args: （未启用）
            quickly: 是否加急载入（未启用）
        '''
        self.img_queue.put([path,args])

    def getTinyImg_async(self, path, args, quickly=False):
        '''
        获取缩略图（异步方式）
        载入后线程会向主线程发信号
        args
            path: str 图片路径
            args: (int,int,int) 需要缩略图的grid的x，y坐标，以及点击时ViewWidget的全局计数器
            quickly: 是否加急载入（未启用）
        '''
        self.tinyimg_queue.put([path,args])

    def close(self):
        '''
        程序关闭时的处理
        向队列发送None请求，让线程退出
        '''
        self.img_queue.put([None,None])
        self.tinyimg_queue.put([None,None])
        # self.p_img.join()
        # self.p_tinyimg.join()
        
    def decodeImg(self, imgBytes):
        '''
        将图片从二进制格式解码成GUI可用的数字形式
        args
            imgBytes:bytes 图片的二进制串
        ret
            QPixmap 图片的数字格式
        '''
        s = io.BytesIO(imgBytes)
        img = Image.open(s).convert('RGBA') #Qt要求4通道
        return img.toqpixmap()

class ImgReadThread(QThread):
    def __init__(self, system):
        super().__init__()
        self.system = system #imgSystem，用来与mainWindow通信
        self.q = system.img_queue #线程队列
        self.pool = system.img_pool #缓存池

    def run(self):
        while True:
            path,_ = self.q.get() #获取新请求
            if path is None: #退出请求
                break

            if self.pool.has(path):
                continue
            img_b = open(path, 'rb').read()
            self.pool.add(path, img_b)
            self.system.mainWindow.imgReady.emit(path) #回调信号

class TinyImgReadThread(QThread):
    def __init__(self, system):
        super().__init__()
        self.system = system #imgSystem，用来与mainWindow通信
        self.q = system.tinyimg_queue #线程队列
        self.pool = system.tinyimg_pool #缓存池
        self.img_extnames = system.img_extnames #图片后缀列表
        self.tinyimg_filedir = system.tinyimg_filedir #缩略图保存目录

    def run(self):
        try:
            self.run2()
        except:
            print("thread error")
            raise

    def run2(self):
        while True:
            path,args = self.q.get() #获取请求
            if path is None: #退出请求
                break

            if not self.pool.has(path):
                dirpath = os.path.dirname(path)
                pkl_dirpath = self.translate_path(dirpath) #计算缩略图所属目录的缓存文件的路径
                if os.path.exists(pkl_dirpath): 
                    #如果该目录缓存过，则加载该文件即可
                    data = pickle.load(open(pkl_dirpath,'rb'))
                    for path,img_b in data.items():
                        self.pool.add(path,img_b)
                else:
                    #否则，需要读入该目录的所有图片，然后生成缩略图，再保存成文件
                    names = os.listdir(dirpath)
                    img_paths = []
                    # 获取该目录的所有图片路径
                    for name in names:
                        img_path = os.path.join(dirpath,name)
                        if os.path.isfile(img_path) and os.path.splitext(img_path)[1] in self.img_extnames:
                            img_paths.append(img_path)
                    imgs = {}
                    for img_path in img_paths:
                        img = Image.open(img_path).convert('RGB') #载入图片
                        tinyimg,tinyimg_b = self.make_tinyimg(img) #生成缩略图
                        self.pool.add(img_path, tinyimg_b) #缓存
                        imgs[img_path] = tinyimg_b
                    pickle.dump(imgs, open(pkl_dirpath,'wb')) #该目录的所有缩略图一并保存成文件

            self.system.mainWindow.tinyImgReady.emit(path, *args) #发送回调信号

    def translate_path(self, path):
        '''
        计算目标目录对应的缓存文件保存路径
        规则是：
            1. 目录是缩略图缓存目录
            2. 文件名是目标目录中将所有目录分割符换成'_'，然后在后缀前加上目录的md5的前10位
        args
            path:str 目标目录
        ret
            str 对应的缓存文件保存路径
        '''
        path_md5 = md5(path.encode()).hexdigest()
        path = path.replace('\\','_').replace(':','')
        return os.path.join(self.tinyimg_filedir, f"{path}_{path_md5[:10]}.pkl")

    def make_tinyimg(self, img):
        '''
        用原图生成缩略图
        两个步骤：
            1. 缩放 
            2. 生成二进制串
        args
            img: PIL.Image 原图图片
        ret
            (PIL.Image,bytes) 缩略图图片和对应的二进制串
        '''
        max_hw = self.system.mainWindow.global_args['tinyimg_size']
        w,h = img.size
        ratio = max(w,h) / max_hw
        w2,h2 = round(w/ratio),round(h/ratio)
        tinyimg = img.resize((w2,h2))
        s = io.BytesIO()
        tinyimg.save(s,'jpeg')
        s.seek(0)
        tinyimg_b = s.read()
        return tinyimg,tinyimg_b


class CachedPool(object):
    def __init__(self, pool_size):
        self.pool_size = pool_size #缓存池大小
        self.k2v = collections.OrderedDict() #核心数据结构，Ordered用于保证先进先出
        self.lock = threading.Lock() #互斥锁，保证线程安全

    def add(self, k, v):
        '''
        增加操作
        args
            k:str 图片路径
            v:bytes 图片二进制串
        '''
        assert k not in self.k2v, f'multi add the same key:{k}'
        self.lock.acquire()
        if len(self.k2v) == self.pool_size:
            self.k2v.popitem(False)
        self.k2v[k] = v
        self.lock.release()
    
    def get(self, k):
        '''
        获取操作
        args
            k:str 图片路径
        '''
        assert k in self.k2v, f'no this key to get:{k}'
        self.lock.acquire()
        v = self.k2v[k]
        self.k2v.move_to_end(k)
        self.lock.release()
        return v

    def has(self, k):
        '''
        判断是否已缓存
        args
            k:str 图片路径
        '''
        return k in self.k2v
