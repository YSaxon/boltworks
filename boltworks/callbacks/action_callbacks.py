from __future__ import annotations
import inspect

import re
import uuid
from collections import ChainMap
from typing import Optional, Protocol, Sequence, Union

from slack_bolt import Args
from slack_bolt.app import App
from slack_bolt.response.response import BoltResponse
from ..helper.kvstore import KVStoreWithSerializer
from slack_sdk.models.blocks import ButtonElement, StaticSelectElement
from slack_sdk.models.blocks.block_elements import Option, PlainTextObject
from slack_sdk.webhook import WebhookResponse

prefix_for_callback="rcb_"

class ActionCallbackFunction(Protocol):
     def __call__(self, args:Args): ...
class ActionValueCallbackFunction(Protocol):
     def __call__(self, args:Args, value:Optional[str]): ...
class ViewCallbackFunction(Protocol):
     def __call__(self, args:Args, flat_values:dict[str,str]): ...


class ActionCallbacks:
    def __init__(self,app:App,cache:KVStoreWithSerializer) -> None:
        self._cache=cache
        app.action(re.compile(prefix_for_callback+'.*'))(self._do_callback_action)
        app.view(re.compile(prefix_for_callback+'.*'))(self._do_callback_view)

    def _do_callback_action(self,args:Args):
        args.ack()
        if args.action:
            callback_key=args.action['action_id'][len(prefix_for_callback):]
            callback_func=self._cache[callback_key]
            if "value" in inspect.signature(callback_func).parameters:
                value = args.action['selected_option']['value'] if 'selected_option' in args.action and 'value' in args.action['selected_option'] else None  #menu option   
                response=callback_func(args=args,value=value)
            else:
                response=callback_func(args=args)
            return response
        
    def get_button_register_callback(self,
                    text,
                    callback_action:ActionCallbackFunction,
                    **formattingOptions)->ButtonElement:
        callback_key=str(uuid.uuid1())
        button=ButtonElement(
            text=text,
            action_id=prefix_for_callback+callback_key,
            **formattingOptions
        )
        self._cache[callback_key]=callback_action
        return button

    def _do_callback_view(self,args:Args,view):
        args.ack()
        callback_key=view['callback_id'][len(prefix_for_callback):]
        values=dict(ChainMap(*view["state"]['values'].values())) #if "state" in view and "values" in view["state"] else None
        # values_copy=copy.deepcopy(values)
        flat_values=self._flatten_values(values)#_copy)
        callback_func:ViewCallbackFunction=self._cache[callback_key]
        callback_func(flat_values=flat_values,args=args)

    def get_menu_register_callback(self,
        options:Optional[Sequence[Union[dict, Option]]],
        placeholder: Optional[Union[str, PlainTextObject]],
        callback_action:ActionValueCallbackFunction,
        **formattingOptions)->StaticSelectElement:
            callback_key=str(uuid.uuid1())
            self._cache[callback_key]=callback_action
            menu=StaticSelectElement(
                placeholder=placeholder,
                options=options,
                action_id=prefix_for_callback+callback_key,
                **formattingOptions)
            return menu

    def generate_callback_id_for_modal_register_callback(self,
        callback_action:ViewCallbackFunction
    ):
        callback_key=str(uuid.uuid1())
        self._cache[callback_key]=callback_action
        callback_id=prefix_for_callback+callback_key
        return callback_id

    def _flatten_values(self,values):# this whole thing is specifically to parse the various types of values returned by different slack input fields and return a common value
        return_dict:dict[str,str]=dict()
        for action_id,raw_value_dict in values.items():
            raw_value_dict.pop('type')
            value_of_other_key=raw_value_dict.popitem()[1]#remaining one that doesnt equal type
            if len(raw_value_dict)>0:
                raise NotImplementedError("this code as-is only works if the dict only contains 'type' and one other key")
            elif value_of_other_key is None:
                return_dict[action_id]=""
            elif isinstance(value_of_other_key,str):#could combine None and str with an OR, but leaving seperate for clarity
                return_dict[action_id]=value_of_other_key
            elif isinstance(value_of_other_key,list):
                raise NotImplementedError("should be easy to implement this but we haven't yet, you'll need to check if the list is of values or of further dicts")
                return_dict[action_id]=value_of_other_key
            elif isinstance(value_of_other_key,dict):
                if 'value' in value_of_other_key and isinstance(value_of_other_key['value'],str):
                    return_dict[action_id]=value_of_other_key['value']
                else:
                    raise NotImplementedError("looks like a different type of field we haven't implemented yet")
            else:
                raise NotImplementedError("looks like a different type of field we haven't implemented yet")
        return return_dict
