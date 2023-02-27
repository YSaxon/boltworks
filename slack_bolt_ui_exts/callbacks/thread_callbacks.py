import re
from typing import Any, Callable

from slack_bolt import App, Args
from slack_bolt_ui_exts.helper.kvstore import KVStoreWithSerializer


class MsgThreadCallbacks():
    def __init__(self,app:App,kvstore:KVStoreWithSerializer):
        self._callback_store=kvstore.namespaced("thread_callback")
        app.message(re.compile('.*'))(self.check_for_thread_reply_callback)

    def register_thread_reply_callback(self, ts:str, callback:Callable[[Args],Any]):
        self._callback_store[ts]=callback

    def check_for_thread_reply_callback(self,args:Args):
        if 'thread_ts' in args.payload:
            thread_ts=args.payload['thread_ts']
            if thread_ts in self._callback_store:
                callback=self._callback_store[thread_ts]
                callback(args)
