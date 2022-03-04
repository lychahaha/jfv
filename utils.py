import os,sys
import collections

class CachedPool(object):
    def __init__(self, pool_size):
        self.pool_size = pool_size
        self.cur_time = 0
        self.k2v = collections.OrderedDict()

    def add(self, k, v):
        assert k not in self.k2v, f'multi add the same key:{k}'
        if len(self.k2v) == self.pool_size:
            self.k2v.popitem(False)
        self.k2v[k] = v
    
    def get(self, k):
        assert k in self.k2v, f'no this key to get:{k}'
        v = self.k2v[k]
        self.k2v.move_to_end(k)
        return v

    def has(self, k):
        return k in self.k2v
    