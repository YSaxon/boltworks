

import copy
import json
import pytest
from slack_bolt import App
from ..boltworks import *
from typing import Tuple
from unittest.mock import Mock
from diskcache import Cache
import dill
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .common import TOKEN,APPTOKEN, TEST_CHANNEL, assert_block_text_equals, fake_a_respond_from_response, get_blocks_from_response_with_assertions




DISK_CACHE_DIR="/tmp/diskcache"


@pytest.fixture
def fixture():  
    app = App(token=TOKEN)
    handler=SocketModeHandler(app,app_token=APPTOKEN)
    handler.connect()
    
    disk_cache=Cache(directory=DISK_CACHE_DIR)
    kvstore=DiskCacheKVStore(disk_cache).using_serializer(dill)
    treeui=TreeNodeUI(app,kvstore)
    
    yield app,treeui
    
    disk_cache.close()
    handler.disconnect()
    
    
def test_simple_actual_post(fixture:Tuple[App,TreeNodeUI]):
    app,treeui=fixture
    rootnode=TreeNode.withSimpleSideButton("parent",[TreeNode("child1"), TreeNode("child2")])
    response=treeui.post_single_node(TEST_CHANNEL,rootnode)
    blocks=get_blocks_from_response_with_assertions(response)
    assert len(blocks)==1
    assert_block_text_equals(blocks[0],"parent")
    assert 'accessory' in blocks[0]
    
    
def test_simple_actualpost_mockexpand(fixture:Tuple[App,TreeNodeUI]):
    app,treeui=fixture
    rootnode=TreeNode.withSimpleSideButton("parent",[TreeNode("child1"), TreeNode("child2")])
    response=treeui.post_single_node(TEST_CHANNEL,rootnode)
    blocks=get_blocks_from_response_with_assertions(response)
    button=blocks[0]['accessory']
    
    ack=Mock()
    respond=Mock()
    treeui._do_callback_action(action=button,ack=ack,respond=respond)
    
    ack.assert_called_once()
    respond.assert_called_once()
    
    assert respond.call_args.kwargs['replace_original']
    replace_blocks=respond.call_args.kwargs['blocks']
    
    assert len(replace_blocks)==3
    assert_block_text_equals(replace_blocks[0],'parent')
    assert_block_text_equals(replace_blocks[1],'child1')
    assert_block_text_equals(replace_blocks[2],'child2')

    
def test_simple_actualpost_actualexpand(fixture:Tuple[App,TreeNodeUI]):
    app,treeui=fixture
    rootnode=TreeNode.withSimpleSideButton("parent",[TreeNode("child1"), TreeNode("child2")])
    response=treeui.post_single_node(TEST_CHANNEL,rootnode)
    blocks=get_blocks_from_response_with_assertions(response)
    button=blocks[0]['accessory']
    
    ack=Mock()
    respond=fake_a_respond_from_response(response)
    callback_response=treeui._do_callback_action(action=button,ack=ack,respond=respond)
    
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    
    assert len(callback_blocks)==3
    assert_block_text_equals(callback_blocks[0],'parent')
    assert_block_text_equals(callback_blocks[1],'child1')
    assert_block_text_equals(callback_blocks[2],'child2')
    
    
def test_complex_actual_multibutton(fixture:Tuple[App,TreeNodeUI]):
    app,treeui=fixture
    
    
    ANodes=[TreeNode(f"A{i}") for i in range(13)]
    BNodes=[TreeNode(f"B{i}") for i in range(10)]
    CNodes=[TreeNode(f"C{i}") for i in range(9)]
    CNode3Children=[TreeNode(f"C3_{i}") for i in range(3)]
    CNodes[3].children_containers=[ButtonChildContainer(CNode3Children)]
    CNodes[3].first_child_container_on_side=True
    
    rootnode=TreeNode(
        "parent",
       children_containers=[
           ButtonChildContainer(ANodes,static_button_text="Alpha",child_pageination=5),
           ButtonChildContainer(BNodes,static_button_text="Bravo",child_pageination=5),
           ButtonChildContainer(CNodes,static_button_text="Charlie",child_pageination=10),
       ]
    )
                      
    response=treeui.post_single_node(TEST_CHANNEL,rootnode)
    blocks=get_blocks_from_response_with_assertions(response)
    
    assert len(blocks)==2 #parent + actions
    button_b=blocks[1]['elements'][1]
    assert_block_text_equals(button_b,"Bravo")
    
    ack=Mock()
    respond=fake_a_respond_from_response(response)
    
    #expand bravo
    callback_response=treeui._do_callback_action(action=button_b,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert len(callback_blocks)==8 #parent+actions+5 children+navigation
    assert_block_text_equals(callback_blocks[0],'parent')
    assert_block_text_equals(callback_blocks[2],'B0')
    assert_block_text_equals(callback_blocks[-2],'B4')
    
    #expand alpha
    button_a=callback_blocks[1]['elements'][0]
    callback_response=treeui._do_callback_action(action=button_a,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert len(callback_blocks)==8 #parent+actions+5 children+navigation
    assert_block_text_equals(callback_blocks[0],'parent')
    assert_block_text_equals(callback_blocks[2],'A0')
    
    #page forward alpha
    button_forward=callback_blocks[-1]['elements'][-1]
    callback_response=treeui._do_callback_action(action=button_forward,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert len(callback_blocks)==8 #parent+actions+5 children+navigation
    assert_block_text_equals(callback_blocks[0],'parent')
    assert_block_text_equals(callback_blocks[2],'A5')
    
    #page forward alpha
    button_forward=callback_blocks[-1]['elements'][-1]
    callback_response=treeui._do_callback_action(action=button_forward,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert len(callback_blocks)==6 #parent + actions + 3 children + navigation
    assert_block_text_equals(callback_blocks[0],'parent')
    assert_block_text_equals(callback_blocks[2],'A10')
    
    #page backwards alpha
    button_forward=callback_blocks[-1]['elements'][0]
    callback_response=treeui._do_callback_action(action=button_forward,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert len(callback_blocks)==8 #parent+actions+5 children+navigation
    assert_block_text_equals(callback_blocks[0],'parent')
    assert_block_text_equals(callback_blocks[2],'A5')
    
    #contract alpha
    button_a=callback_blocks[1]['elements'][0]
    callback_response=treeui._do_callback_action(action=button_a,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert len(callback_blocks)==2 #parent + actions
    
    #expand charlie
    button_c=callback_blocks[1]['elements'][2]
    callback_response=treeui._do_callback_action(action=button_c,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert len(callback_blocks)==11 #parent + actions + 9 children
    
    #expand c3
    c3=callback_blocks[2+3]
    c3_button=c3['accessory']
    callback_response=treeui._do_callback_action(action=c3_button,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert len(callback_blocks)==11+3 #parent + actions + 9 children + 3 subchildren
    
    
    
def test_complex_actual_overflowmenu(fixture:Tuple[App,TreeNodeUI]):
    app,treeui=fixture
    
    
    AOption=MenuOption("Alpha",[TreeNode(f"A{i}") for i in range(13)])
    BOption=MenuOption("Bravo",[TreeNode(f"B{i}") for i in range(10)])
    COption=MenuOption("Charlie",[TreeNode(f"C{i}") for i in range(5)])
    # CNode3Children=[TreeNode(f"C3_{i}") for i in range(3)]
    # COption.nodes[3].children_containers.append(ButtonChildContainer(CNode3Children))
    # COption.nodes[3].first_child_container_on_side=True
    
    rootnode=TreeNode(
        "parent",
       children_containers=[   
           OverflowMenuChildContainer([AOption,BOption,COption],child_pageination=5),
       ],
       first_child_container_on_side=False
    )
                      
    response=treeui.post_single_node(TEST_CHANNEL,rootnode)
    blocks=get_blocks_from_response_with_assertions(response)
    
    assert len(blocks)==2 #parent + actions
    menu=blocks[1]['elements'][0]
    assert_block_text_equals(menu['options'][1],"Bravo")
    
    ack=Mock()
    respond=fake_a_respond_from_response(response)
    
    #expand bravo
    action_for_optionb=dict(action_id=menu['action_id'],selected_option=menu['options'][1])
    callback_response=treeui._do_callback_action(action=action_for_optionb,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert len(callback_blocks)==8 #parent+actions+5 children+navigation
    assert_block_text_equals(callback_blocks[0],'parent')
    assert_block_text_equals(callback_blocks[2],'B0')
    assert_block_text_equals(callback_blocks[-2],'B4')

def test_complex_actual_menuoption(fixture:Tuple[App,TreeNodeUI]):
    app,treeui=fixture
    
    
    AOption=MenuOption("Alpha",[TreeNode(f"A{i}") for i in range(13)])
    BOption=MenuOption("Bravo",[TreeNode(f"B{i}") for i in range(10)])
    COption=MenuOption("Charlie",[TreeNode(f"C{i}") for i in range(9)])
    CNode3Children=[TreeNode(f"C3_{i}") for i in range(3)]
    COption.nodes[3].children_containers.append(ButtonChildContainer(CNode3Children))
    COption.nodes[3].first_child_container_on_side=True
    
    rootnode=TreeNode(
        "parent",
       children_containers=[   
           StaticSelectMenuChildContainer([AOption,BOption,COption],child_pageination=5),
       ],
       first_child_container_on_side=False
    )
                      
    response=treeui.post_single_node(TEST_CHANNEL,rootnode)
    blocks=get_blocks_from_response_with_assertions(response)
    
    assert len(blocks)==2 #parent + actions
    menu=blocks[1]['elements'][0]
    assert_block_text_equals(menu['options'][1],"Bravo")
    
    ack=Mock()
    respond=fake_a_respond_from_response(response)
    
    #expand bravo
    action_for_optionb=dict(action_id=menu['action_id'],selected_option=menu['options'][1])
    callback_response=treeui._do_callback_action(action=action_for_optionb,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert len(callback_blocks)==8 #parent+actions+5 children+navigation
    assert_block_text_equals(callback_blocks[0],'parent')
    assert_block_text_equals(callback_blocks[2],'B0')
    assert_block_text_equals(callback_blocks[-2],'B4')
    
    #expand alpha
    menu=callback_blocks[1]['elements'][0]
    action_for_optiona=dict(action_id=menu['action_id'],selected_option=menu['options'][1+0]) #need to add one for the deselect option on top
    callback_response=treeui._do_callback_action(action=action_for_optiona,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert len(callback_blocks)==8 #parent+actions+5 children+navigation
    assert_block_text_equals(callback_blocks[0],'parent')
    assert_block_text_equals(callback_blocks[2],'A0')
    
    #page forward alpha
    button_forward=callback_blocks[-1]['elements'][-1]
    callback_response=treeui._do_callback_action(action=button_forward,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert len(callback_blocks)==8 #parent+actions+5 children+navigation
    assert_block_text_equals(callback_blocks[0],'parent')
    assert_block_text_equals(callback_blocks[2],'A5')
    
    # #page forward alpha
    # button_forward=callback_blocks[-1]['elements'][-1]
    # callback_response=treeui._do_callback_action(action=button_forward,ack=ack,respond=respond)
    # callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    # assert len(callback_blocks)==6 #parent + actions + 3 children + navigation
    # assert_block_text_equals(callback_blocks[0],'parent')
    # assert_block_text_equals(callback_blocks[2],'A10')
    
    # #page backwards alpha
    # button_forward=callback_blocks[-1]['elements'][0]
    # callback_response=treeui._do_callback_action(action=button_forward,ack=ack,respond=respond)
    # callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    # assert len(callback_blocks)==8 #parent+actions+5 children+navigation
    # assert_block_text_equals(callback_blocks[0],'parent')
    # assert_block_text_equals(callback_blocks[2],'A5')
    
    #contract all
    menu=callback_blocks[1]['elements'][0]
    action_for_deselect=dict(action_id=menu['action_id'],selected_option=menu['options'][0])
    callback_response=treeui._do_callback_action(action=action_for_deselect,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert len(callback_blocks)==2 #parent + actions
    
    #expand charlie
    menu=callback_blocks[1]['elements'][0]
    action_charlie=dict(action_id=menu['action_id'],selected_option=menu['options'][-1])
    callback_response=treeui._do_callback_action(action=action_charlie,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert len(callback_blocks)==8 #parent+actions+5 children+navigation
    assert_block_text_equals(callback_blocks[0],'parent')
    assert_block_text_equals(callback_blocks[2],'C0')
    
    #expand c3
    c3=callback_blocks[2+3]
    c3_button=c3['accessory']
    callback_response=treeui._do_callback_action(action=c3_button,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert len(callback_blocks)==8+3 #parent+actions+5 children+navigation + 3 grandchildren
    
    
    
#sample json obtained from chatgpt
json1 =  """
  {
  "name": "John Doe",
  "age": 30,
  "phoneNumbers": [
    {
      "type": "home",
      "number": "555-1234"
    },
    {
      "type": "work",
      "number": "555-5678",
      "extension": "123"
    }
  ],
  "emails": [
    "john.doe@example.com",
    "jdoe@example.com"
  ],
  "isMarried": false,
  "favoriteColors": {
    "primary": "blue",
    "secondary": "green"
  },
  "address": {
    "street": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "zip": "12345",
    "coordinates": {
      "latitude": 37.1234,
      "longitude": -122.1234
    }
  },
  "nullValue": null,
  "emptyValue": ""
}
"""

    
def test_json_helper_method(fixture:Tuple[App,TreeNodeUI]):
    app,treeui=fixture
    
    loaded_json=json.loads(json1)
    
    rootnode=TreeNode(
        "json",
       children_containers=[
           ButtonChildContainer.forJsonDetails(loaded_json)
       ]
    )
                      
    response=treeui.post_single_node(TEST_CHANNEL,rootnode)
    blocks=get_blocks_from_response_with_assertions(response)
    button=blocks[0]['accessory']
    
    #expand details
    ack=Mock()
    respond=fake_a_respond_from_response(response)
    callback_response=treeui._do_callback_action(action=button,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert '5' in callback_blocks[-1]['accessory']['text']['text']
    
    #expand final button
    final_button=callback_blocks[-1]['accessory']
    callback_response=treeui._do_callback_action(action=final_button,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert '2' in callback_blocks[-1]['accessory']['text']['text']
    
    #expand new final button
    final_button=callback_blocks[-1]['accessory']
    callback_response=treeui._do_callback_action(action=final_button,ack=ack,respond=respond)
    callback_blocks=get_blocks_from_response_with_assertions(callback_response)
    assert 'longitude: -122.1234' in callback_blocks[-1]['text']['text']
    
    
   
