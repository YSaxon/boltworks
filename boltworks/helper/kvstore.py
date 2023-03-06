from __future__ import annotations

import contextlib

import diskcache.core
from .serializers import Serializer


class KVStore:
    def __getitem__(self, key): ...
    def __setitem__(self, key, value): ...
    def __delitem__(self, key): ...
    def __contains__(self, key): ...

    @contextlib.contextmanager
    def transact(self, retry=False):...

    def namespaced(self,prefix:str)->KVStore:...

    def using_serializer(self,serializer:Serializer):
        return KVStoreWithSerializer(self,serializer)

class KVStoreWithSerializer(KVStore):
    def __init__(self,kvstore:KVStore,serializer:Serializer):
        if isinstance(kvstore,KVStoreWithSerializer):
            self._inner_kvstore:KVStore=kvstore._inner_kvstore #so we don't wind up serializing twice
        else:
            self._inner_kvstore=kvstore
        self._serializer=serializer

    def __getitem__(self, key):
        serialized=self._inner_kvstore[key]
        return self._serializer.loads(serialized) \
            if isinstance(serialized,bytes) else serialized #transitional

    def __setitem__(self, key, value):
        serialized=self._serializer.dumps(value)
        self._inner_kvstore[key]=serialized

    def __delitem__(self, key): return self._inner_kvstore.__delitem__(key)
    def __contains__(self, key): return self._inner_kvstore.__contains__(key)

    @contextlib.contextmanager
    def transact(self, retry=False):
        with self._inner_kvstore.transact(retry):
            yield

class DiskCacheKVStore(KVStore):
    def __init__(self,disk_cache:diskcache.core.Cache,prefix:str="") -> None:
        self._prefix=prefix
        self._diskcache=disk_cache

    def _prefixed(self,key):
        return f"{self._prefix}{key}"

    def __getitem__(self, key): return self._diskcache[self._prefixed(key)]
    def __setitem__(self, key, value): self._diskcache[self._prefixed(key)]=value
    def __delitem__(self, key): del self._diskcache[self._prefixed(key)]
    def __contains__(self, key): return self._prefixed(key) in self._diskcache

    @contextlib.contextmanager
    def transact(self, retry=False):
        with self._diskcache.transact(retry):
            yield

    def namespaced(self,prefix:str): return DiskCacheKVStore(self._diskcache,prefix)
