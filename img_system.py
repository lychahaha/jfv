import os
import collections
import threading
import multiprocessing
from hashlib import md5
import pickle

class ImgSystem(object):
    def __init__(self, img_poolsize, tinyimg_poolsize, img_extnames, tinyimg_filedir):
        self.img_poolsize = img_poolsize
        self.tinyimg_poolsize = tinyimg_poolsize
        self.img_extnames = img_extnames
        self.tinyimg_filedir = tinyimg_filedir

        self.img_pool = CachedPool(self.img_poolsize)
        self.tinyimg_pool = CachedPool(self.tinyimg_poolsize)

        self.img_queue = multiprocessing.Queue()
        self.tinyimg_queue = multiprocessing.Queue()

        self.p_img = ImgReadThread(self.img_queue, self.img_pool)
        self.p_tinyimg = TinyImgReadThread(self.tinyimg_queue, self.tinyimg_pool, self.img_extnames, self.tinyimg_filedir)

        self.p_img.start()
        self.p_tinyimg.start()

    def getImg(self, path):
        return self.decodeImg(self.img_pool.get(path))

    def getTinyImg(self, path):
        return self.decodeImg(self.tinyimg_pool.get(path))

    def hasImg(self, path):
        return self.img_pool.has(path)

    def hasTinyImg(self, path):
        return self.tinyimg_pool.has(path)

    def getImg_async(self, path, callback, quickly=False):
        self.img_queue.put([path,callback])

    def getTinyImg_async(self, path, callback, quickly=False):
        self.tinyimg_queue.put([path,callback])

    def close(self):
        self.img_queue.put([None,None])
        self.tinyimg_queue.put([None,None])
        self.p_img.join()
        self.p_tinyimg.join()
        
    def decodeImg(self, imgBytes):
        pass

class ImgReadThread(threading.Thread):
    def __init__(self, q, pool):
        super().__init__()
        self.q = q
        self.pool = pool

    def run(self):
        while True:
            path,callback = self.q.get()
            if path is None:
                break

            if self.pool.has(path):
                continue
            img_b = open(path, 'rb').read()
            self.pool.add(path, img_b)
            callback()

class TinyImgReadThread(threading.Thread):
    def __init__(self, q, pool, img_extnames, tinyimg_filedir):
        super().__init__()
        self.q = q
        self.pool = pool
        self.img_extnames = img_extnames
        self.tinyimg_filedir = tinyimg_filedir

    def run(self):
        while True:
            path,callback = self.q.get()
            if path is None:
                break

            if not self.pool.has(path):
                dirpath = os.path.dirname(path)
                pkl_dirpath = self.translate_path(dirpath)
                if os.path.exists(pkl_dirpath):
                    data = pickle.load(open(pkl_dirpath,'rb'))
                    for path,img_b in data.items():
                        self.pool.add(path,img_b)
                else:
                    names = os.listdir(dirpath)
                    img_paths = []
                    for name in names:
                        img_path = os.path.join(dirpath,name)
                        if os.path.isfile(img_path) and os.path.splitext(img_path)[1] in self.img_extnames:
                            img_paths.append(img_path)
                    imgs = {}
                    for img_path in img_paths:
                        img_b = open(path, 'rb').read()
                        self.pool.add(img_path.img_b)
                        imgs[img_path] = img_b
                    pickle.dumps(imgs, open(pkl_dirpath,'wb'))

            callback()

    def translate_path(self, path):
        path_md5 = md5(path.encode()).hexdigest()
        path = path.replace('\\','_').replace(':','')
        return os.path.join(self.tinyimg_filedir, path+path_md5[:10]+'.pkl')


class CachedPool(object):
    def __init__(self, pool_size):
        self.pool_size = pool_size
        self.cur_time = 0
        self.k2v = collections.OrderedDict()
        self.lock = threading.Lock()

    def add(self, k, v):
        assert k not in self.k2v, f'multi add the same key:{k}'
        self.lock.acquire()
        if len(self.k2v) == self.pool_size:
            self.k2v.popitem(False)
        self.k2v[k] = v
        self.lock.release()
    
    def get(self, k):
        assert k in self.k2v, f'no this key to get:{k}'
        self.lock.acquire()
        v = self.k2v[k]
        self.k2v.move_to_end(k)
        self.lock.release()
        return v

    def has(self, k):
        return k in self.k2v
