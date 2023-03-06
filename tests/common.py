from __future__ import annotations
from functools import partial
from unittest.mock import Mock

from slack_bolt import App, Args
import slack_bolt
from slack_sdk import WebClient
import slack_sdk
from slack_sdk.models.blocks.blocks import Block
from slack_sdk.web import SlackResponse



def mock_an_args():
    args_mock=Mock(Args)
    respond_mock=Mock()
    say_mock=Mock()
    args_mock.context=dict(user_id="testuserid")
    args_mock.attach_mock(Mock(),"ack")
    args_mock.attach_mock(respond_mock,"respond")
    args_mock.attach_mock(say_mock,"say")
    return args_mock,respond_mock,say_mock


def mock_an_app():
    app_mock=Mock(App)
    client_mock=Mock(WebClient)
    chatPost_mock=Mock(WebClient.chat_postMessage)
    chatPostResponse_mock=Mock(slack_sdk.web.SlackResponse)
    app_mock.attach_mock(client_mock,"client")
    client_mock.attach_mock(chatPost_mock,"chat_postMessage")
    chatPost_mock.return_value(chatPostResponse_mock)
    chatPostResponse_mock.status_code=200
    
    client_mock.attach_mock
    return app_mock,chatPostResponse_mock

# def mock_a_callbacks(app):...
    

def get_blocks_from_response_with_assertions(response:SlackResponse)->list[Block]:
    assert(response.status_code==200)
    assert(isinstance(response.data,dict))
    assert('message' in response.data)
    return response.data['message']['blocks']

def assert_block_text_equals(block:Block|dict,text:str):
    if isinstance(block,Block):
        block=block.to_dict()
    assert block['text']==text or block['text']['text']==text
    



def fake_a_respond(client:slack_sdk.WebClient,channel:str,ts:str=None,user:str=None):
    def respond(blocks=None,text='',replace_original=False):
        if replace_original:
            assert ts #should create with ts to use replace_original
            post=partial(client.chat_update,ts=ts)
        elif user:
            post=partial(client.chat_postEphemeral,user=user)
        else:
            post=client.chat_postMessage
        return post(channel=channel,blocks=blocks,text=text)
    return respond
    # assert(isinstance(response.data,dict))
    # channel=response.data['channel']
    # ts=response.data['ts']
    # return partial(app.client.chat_postMessage,channel=channel,ts=ts,)
    

def fake_a_respond_from_response(response:SlackResponse):
    assert(isinstance(response.data,dict))
    channel=response.data['channel']
    ts=response.data['ts']
    return fake_a_respond(client=response._client,channel=channel,ts=ts)