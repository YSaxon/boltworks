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

from .common import TOKEN, APPTOKEN, TEST_CHANNEL, DISK_CACHE_DIR


@pytest.fixture
def fixture():
    app = App(token=TOKEN)
    handler = SocketModeHandler(app, app_token=APPTOKEN)
    handler.connect()

    disk_cache = DiskCacheKVStore(Cache(directory=DISK_CACHE_DIR))
    callbacks = MsgThreadCallbacks(app, disk_cache.using_serializer(dill))

    yield app, callbacks

    disk_cache._diskcache.close()
    handler.disconnect()


def test(fixture: Tuple[App, MsgThreadCallbacks]):
    app, callbacks = fixture

    response = app.client.chat_postMessage(
        channel=TEST_CHANNEL, text="thread to register callbacks"
    )
    ts = response.data["ts"]  # type: ignore

    callbackfunc = Mock()

    callbacks.register_thread_reply_callback(ts, callbackfunc)

    callbackfunc.assert_not_called()
    app.client.chat_postMessage(
        channel=TEST_CHANNEL, text="testing thread call", thread_ts=ts
    )

    sleep(1)
    callbackfunc.assert_called_once()
