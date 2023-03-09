from datetime import datetime, timedelta
from functools import partial
import json
from time import sleep
from typing import Tuple
from unittest.mock import Mock
from diskcache import Cache
import pytest
from slack_bolt import App, Args
from boltworks import MsgThreadCallbacks, DiskCacheKVStore
import dill
from slack_bolt.adapter.socket_mode import SocketModeHandler
import sys
import os
from slack_sdk.models.blocks import SectionBlock
from slack_sdk.web import SlackResponse

from slack_bolt import Respond, Say

from .common import get_blocks_from_response_with_assertions, mock_an_args

from .common import TOKEN, APPTOKEN, TEST_CHANNEL, DISK_CACHE_DIR, WEBHOOK_URL

@pytest.fixture
def fixture():
    app = App(token=TOKEN)
    handler = SocketModeHandler(app, app_token=APPTOKEN)
    handler.connect()

    disk_cache = DiskCacheKVStore(Cache(directory=DISK_CACHE_DIR))
    callbacks = MsgThreadCallbacks(app, disk_cache.using_serializer(dill))

    yield app, callbacks, disk_cache

    disk_cache._diskcache.close()
    handler.disconnect()


def test_mocked(fixture: Tuple[App, MsgThreadCallbacks,DiskCacheKVStore]):
    app, callbacks,_ = fixture
    
    ts = '123123123.123'

    def callback_func(args:Args):
        args.say('it works')
        

    callbacks.register_thread_reply_callback(ts, callback_func)
    
    
    args=Mock()
    args.payload={"thread_ts":ts}
    mock_say=Mock()
    args.say=mock_say
    
    callbacks._check_for_thread_reply_callback(args)
    
    
    mock_say.assert_called_once_with("it works")

@pytest.mark.skip(reason="this test basically works, but tends to lag when channel gets busy from many tests in parallel, and then fails the suite")
def test_real(fixture: Tuple[App, MsgThreadCallbacks,DiskCacheKVStore]):
    app, callbacks,store = fixture

    response = app.client.chat_postMessage(
        channel=TEST_CHANNEL, text="thread to register callbacks REAL"
    )
    ts = response.data["ts"]
    
    app.client.chat_postMessage(
        channel=TEST_CHANNEL, text="this shouldn't trigger a callback since it's the bot user posting to the thread", thread_ts=ts
    )
    
    assert 'posted' not in store
    
    def callback_func(args:Args):
        store['posted']=args.payload['text']
        args.say(text='callback worked')

        
    callbacks.register_thread_reply_callback(ts, callback_func)    
        
    import slack_sdk.webhook.client #using webhook because a botpost won't trigger the callback
    slack_sdk.webhook.client.WebhookClient(WEBHOOK_URL).send_dict(dict(text="123",thread_ts=ts))
    
    sleep(1) # to give it a chance to call the callback
    
    assert store['posted']=="123"
