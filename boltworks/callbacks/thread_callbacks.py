from functools import partial
import re
from typing import Any, Callable, Protocol

from slack_bolt import App, Args
from ..helper.kvstore import KVStoreWithSerializer

class ThreadCallbackFunction(Protocol):
     def __call__(self, args:Args): ...
     

class MsgThreadCallbacks():
    def __init__(self,app:App,kvstore:KVStoreWithSerializer):
        self._callback_store=kvstore.namespaced("thread_callback")
        app.message(re.compile('.*'))(self._check_for_thread_reply_callback)

    def register_thread_reply_callback(self, ts:str, callback:ThreadCallbackFunction):
        self._callback_store[ts]=callback

    def _check_for_thread_reply_callback(self,args:Args):
        if 'thread_ts' in args.payload:
            thread_ts=args.payload['thread_ts']
            if thread_ts in self._callback_store:
                callback:ThreadCallbackFunction=self._callback_store[thread_ts] # type: ignore
                if not args.respond.response_url: #calling respond will fail
                    if 'user' in args.payload:
                        #for some reason a respond_url is often not provided, so the respond method fails, so just fake it here instead
                        args.respond=partial(args.client.chat_postEphemeral,channel=args.payload['channel'],user=args.payload['user']) # type: ignore
                    else:
                        def fail(**kwargs):
                            raise ValueError("posting with args.respond is unsupported here as Slack provided neither a response_url, nor a username from which we could fake an ephemeral response")
                        args.respond=fail# type: ignore
                #TODO consider either modifying say and respond to say/respond in thread, or adding thread_say, and thread_respond to the args (maybe a custom subclass?)
                callback(args)
