import tempfile
import threading
from time import sleep
import diskcache
import pytest
from ..boltworks import DiskCacheKVStore
from ..boltworks.helper.kvstore import KVStore
from unittest.mock import Mock
import dill
import pickle
from ..boltworks.helper.serializers import SignedSerializer


@pytest.fixture
def disk_cache():
    with tempfile.TemporaryDirectory() as cachedir:
        yield diskcache.core.Cache(cachedir)

@pytest.fixture
def store(disk_cache): # a simple disk cache store so we can have the consitutent tests of all_tests be tests in their own right for clarity if they fail in simplest case
    return DiskCacheKVStore(disk_cache)


def test_setandgetitem(store:KVStore):
    store["k1"] = "1"
    assert store["k1"] == "1"

def test_delitem(store:KVStore):
    store["k4"] = "value"
    del store["k4"]
    assert "k4" not in store

def test_contains(store:KVStore):
    store["k3"] = "value"
    assert "k3" in store
    assert "nonexistent_key" not in store

def test_namespaced(store:KVStore):
    
    store1 = store.namespaced("pre_1")
    assert isinstance(store1, KVStore)
        
    store2 = store.namespaced("pre_2")
    
    store2['k2']=2
    assert 'k2' not in store
    assert 'k2' not in store1
    assert 'k2' in store2
    
    store2_copy = store.namespaced("pre_2")
    
    assert 'k2' in store2_copy
    
def test_context_mgr(store:KVStore):
    store['race_key']=0
    
    stop_flag = threading.Event()
    def increment_key():
        while not stop_flag.is_set():
            store['race_key']=store['race_key']+1
    
    increment_thread = threading.Thread(target=increment_key)
    increment_thread.start()
    
    #without synchronizing with transact
    # initialval= store['race_key']
    # sleep(.05)
    # lessfive=store['race_key']-5
    # sleep(.05)
    # store['race_key']=store['race_key']-5
    # sleep(.05)
    # assert store['race_key'] != lessfive != initialval-5
    
    with store.transact():
        initialval= store['race_key']
        sleep(.05)
        lessfive=store['race_key']-5
        sleep(.05)
        store['race_key']=store['race_key']-5
        sleep(.05)
        assert store['race_key']==lessfive==initialval-5
        
    stop_flag.set()        
    
def test_disk_cache_kvstore_contextmgr(disk_cache):
    store = DiskCacheKVStore(disk_cache)
    test_context_mgr(store)

def all_kvstore_simple_tests(kvstore):
    test_setandgetitem(kvstore)
    test_delitem(kvstore)
    test_contains(kvstore)
    test_namespaced(kvstore)
    test_context_mgr(kvstore)
    
# def test_disk_cache_kvstore(disk_cache):
#     store = DiskCacheKVSTore(disk_cache)
#     t_all_kvstore(store)

def test_overdecorated_kvstore(disk_cache):
    store = DiskCacheKVStore(disk_cache)
    overdecorated_store = store.namespaced("first").using_serializer(pickle).using_serializer(dill).namespaced("second").namespaced("third").using_serializer(pickle)
    all_kvstore_simple_tests(overdecorated_store)

def simplefunc(val,mock):
    mock(val+5)
def test_using_pickle_serializer(disk_cache):
    store = DiskCacheKVStore(disk_cache)
    new_store = store.using_serializer(pickle)
    
    all_kvstore_simple_tests(new_store)
        
    new_store['k7']=simplefunc
    
    mock=Mock()
    new_store['k7'](7,mock)
    mock.assert_called_once_with(12)

def test_using_dill_serializer(disk_cache):
    store = DiskCacheKVStore(disk_cache)
    new_store = store.using_serializer(dill)
    
    all_kvstore_simple_tests(new_store)
    
    store['persist']=2
    store['retval']=8
    def func(addval,mock):
        store['persist']+=addval
        mock()
        return store['retval']
    new_store['k5']=func
    
    obj=new_store['k5']
    mock=Mock()
    ret=obj(1,mock)
    mock.assert_called_once()
    assert ret==8
    assert store['persist']==3
    
    
def test_using_serializer_and_encryption(disk_cache):
    store = DiskCacheKVStore(disk_cache)
    signed_serializer=SignedSerializer(dill,"secret_key")
    new_store = store.using_serializer(signed_serializer)
    
    all_kvstore_simple_tests(new_store)
    
    store['persist']=2
    store['retval']=8
    def func(addval,mock):
        store['persist']+=addval
        mock()
        return store['retval']
    new_store['k5']=func
    
    obj=new_store['k5']
    mock=Mock()
    ret=obj(1,mock)
    mock.assert_called_once()
    assert ret==8
    assert store['persist']==3
    