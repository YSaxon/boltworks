from datetime import datetime, timedelta
from functools import partial
import json
from typing import Tuple
from unittest.mock import Mock
from diskcache import Cache
import pytest
from slack_bolt import App, Args
from boltworks import ActionCallbacks,DiskCacheKVStore
import dill
from slack_bolt.adapter.socket_mode import SocketModeHandler
import sys
import os
from slack_sdk.models.blocks import SectionBlock
from slack_sdk.web import SlackResponse

from slack_bolt import Respond,Say

from .common import get_blocks_from_response_with_assertions, mock_an_args

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../..")

from boltworks import ActionCallbacks
from boltworks import DiskCacheKVStore

from .common import TOKEN,APPTOKEN,TEST_CHANNEL,DISK_CACHE_DIR


@pytest.fixture
def fixture():  
    app = App(token=TOKEN)
    handler=SocketModeHandler(app,app_token=APPTOKEN)
    handler.connect()
    
    disk_cache=DiskCacheKVStore(Cache(directory=DISK_CACHE_DIR))
    callbacks=ActionCallbacks(app,disk_cache.using_serializer(dill))
    
    yield app,callbacks
    
    disk_cache._diskcache.close()
    handler.disconnect()


def test_button_posted_same_as_expected(fixture:Tuple[App, ActionCallbacks]):
    app,callbacks=fixture
    def callback_func(args:Args):
        args.respond("C")
    button=callbacks.get_button_register_callback("(button)",callback_func)
    block=SectionBlock(text="Click here",accessory=button)
    response=app.client.chat_postMessage(blocks=[block],channel=TEST_CHANNEL)
    response_blocks=get_blocks_from_response_with_assertions(response)
    response_button=response_blocks[0]['accessory']
    assert(response_button==button.to_dict())

def test_simple(fixture:Tuple[App, ActionCallbacks]):
    app,callbacks=fixture
    def callback_func(args:Args):
        args.respond("C")
    button=callbacks.get_button_register_callback("(button)",callback_func)
    button=button.to_dict() #assuming test_button_posted_same_as_expected succeeds, this is the same as posting it
        
    args_mock,respond_mock,_=mock_an_args()
    args_mock.action=dict(action_id=button['action_id'])
    callbacks._do_callback_action(args=args_mock)
    respond_mock.assert_called_once_with("C")
    
def test_closure(fixture:Tuple[App, ActionCallbacks]):
    app,callbacks=fixture
    closure_var="A"
    def callback_func(args:Args):
        args.respond(closure_var)
    button=callbacks.get_button_register_callback("(button)",callback_func)
    button=button.to_dict() #assuming test_button_posted_same_as_expected succeeds, this is the same as posting it
    
    args_mock,respond_mock,_=mock_an_args()
    args_mock.action=dict(action_id=button['action_id'])
    callbacks._do_callback_action(args=args_mock)
    respond_mock.assert_called_once_with("A")
    
    
def test_partial_with_injected_var(fixture:Tuple[App, ActionCallbacks]):
    app,callbacks=fixture
    def callback_func(args:Args,other_param):
        args.respond(other_param)
    button=callbacks.get_button_register_callback("(button)",partial(callback_func,other_param="B"))
    button=button.to_dict() #assuming test_button_posted_same_as_expected succeeds, this is the same as posting it
          
    args_mock,respond_mock,_=mock_an_args()
    args_mock.action=dict(action_id=button['action_id'])
    callbacks._do_callback_action(args=args_mock)
    respond_mock.assert_called_once_with("B")