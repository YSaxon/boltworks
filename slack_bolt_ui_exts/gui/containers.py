from __future__ import annotations

from typing import Optional

from slack_bolt_ui_exts.gui.expandpointer import ExpandPointer
from slack_bolt_ui_exts.gui.nodes import (
    NAMELESS_FMT_STR_COLLAPSE, NAMELESS_FMT_STR_EXPAND, TreeNode, TreeNodeUI,
    _jsonlike_to_treenode_and_truenum_children)
from slack_sdk.models.blocks import (InteractiveElement, OverflowMenuElement,
                                     RadioButtonsElement, StaticSelectElement)
from slack_sdk.models.blocks.block_elements import Option


class ChildNodeContainer:
    child_nodes:list[TreeNode]
    child_pageination:int=10
    def format_container(self,rootkey:str,pointer_to_container:ExpandPointer,child_already_selected:int=-1)->InteractiveElement:...

class MenuOption:
    def __init__(self,label:str,nodes:list[TreeNode],pageination:int=10):
        self.label=label
        self.nodes=nodes
        self.pageination=pageination
    @staticmethod
    def fromJson(label:str,json:list|dict,pageination=15,optimize_blocks=True):
        children,numchildren=_jsonlike_to_treenode_and_truenum_children(json,pageination=pageination,optimize_blocks=optimize_blocks)
        return MenuOption(label.format(numchildren),children)

class ChildNodeMenuContainer:
    child_nodes:list[list[TreeNode]]
    child_pageination:int=10
    def format_container(self,rootkey:str,pointer_to_container:ExpandPointer,child_already_selected:int=-1,)->InteractiveElement:...


class ButtonChildContainer(ChildNodeContainer):
    """The most basic child node container, this represents a button

    Args:
        ChildNodeContainer (_type_): _description_
    """
    def __init__(self,child_nodes:list[TreeNode],expand_button_format_string:str=NAMELESS_FMT_STR_EXPAND,collapse_button_format_string:str=NAMELESS_FMT_STR_COLLAPSE,static_button_text:Optional[str]=None,child_pageination:int=10):
        self.child_nodes=child_nodes
        self.expand_button_format_string=expand_button_format_string if not static_button_text else static_button_text
        self.collapse_button_format_string = collapse_button_format_string if not static_button_text else static_button_text
        self.child_pageination=child_pageination
    def format_container(self, rootkey:str,pointer_to_container:ExpandPointer, child_already_selected:int=-1) -> InteractiveElement:
        if child_already_selected == -1:#if not already selected then it should be an expand button
            return TreeNodeUI._button_to_replace_block(rootkey=rootkey,
                                                       expandpointer=pointer_to_container.append(0) #appending 0 to point to first node contained within this button
                                                       ,button_text=self.expand_button_format_string.format(len(self.child_nodes)))
        else:
            return TreeNodeUI._button_to_replace_block(rootkey=rootkey,expandpointer=pointer_to_container[:-1] #slicing off the last one to collapse this container and only show it's containing node
                                                       ,button_text=self.collapse_button_format_string.format(len(self.child_nodes)),style="danger")
    @staticmethod
    def forJsonDetails(jsonlike:list|dict,name:str="details",pageination=15,optimize_blocks=True):
        children,numchildren=_jsonlike_to_treenode_and_truenum_children(jsonlike,optimize_blocks=optimize_blocks,_level=0,pageination=pageination)
        return ButtonChildContainer(
                            children,
                            expand_button_format_string=name.format(numchildren) if name else NAMELESS_FMT_STR_EXPAND.format(numchildren),
                            collapse_button_format_string=name.format(numchildren) if name else NAMELESS_FMT_STR_COLLAPSE.format(numchildren),
                            child_pageination=pageination)

class StaticSelectMenuChildContainer(ChildNodeMenuContainer):
    def __init__(self,menu_options_and_associated_nodes:list[MenuOption],placeholder:Optional[str]=None,child_pageination:int=10):
        labels=list(i.label.format(len(i.nodes)) for i in menu_options_and_associated_nodes)
        self.child_nodes=list(i.nodes for i in menu_options_and_associated_nodes)
        self.placeholder=placeholder
        self.options_for_menu=[Option(value=str(i),label=labels[i]) for i in range(len(labels))]
        self.child_pageination=child_pageination
    def format_container(self, rootkey:str,pointer_to_container:ExpandPointer, child_already_selected:int=-1) -> InteractiveElement:
        if child_already_selected == -1: #not already selected
            return StaticSelectElement(placeholder=self.placeholder or "",action_id=TreeNodeUI._serialize_callback(rootkey,pointer_to_container),
                                 options=self.options_for_menu)
        else: #one of the options already selected
            return StaticSelectElement(placeholder=self.placeholder or "",action_id=TreeNodeUI._serialize_callback(rootkey,pointer_to_container),
                                       initial_option=self.options_for_menu[child_already_selected],
                                    options=[Option(value=str(-1),label=""), *self.options_for_menu])

class OverflowMenuChildContainer(ChildNodeMenuContainer):
    def __init__(self,menu_options_and_associated_nodes:list[MenuOption],child_pageination:int=10):
        labels=list(i.label.format(len(i.nodes)) for i in menu_options_and_associated_nodes)
        self.child_nodes=list(i.nodes for i in menu_options_and_associated_nodes)
        self.options_for_menu=[Option(value=str(i),label=labels[i]) for i in range(len(labels))]
        self.child_pageination=child_pageination
    def format_container(self, rootkey:str,pointer_to_container:ExpandPointer, child_already_selected:int=-1) -> InteractiveElement:
        if child_already_selected == -1: #not already selected
            return OverflowMenuElement(action_id=TreeNodeUI._serialize_callback(rootkey,pointer_to_container),options=self.options_for_menu)
        else: #one of the options already selected
            return OverflowMenuElement(action_id=TreeNodeUI._serialize_callback(rootkey,pointer_to_container),options=
                                       [    *self.options_for_menu[:child_already_selected],
                                           Option(value=str(-1),label=f"> {self.options_for_menu[child_already_selected].label}"),
                                           *self.options_for_menu[child_already_selected+1:],
                                           ])

class RadioButtonChildContainer(ChildNodeMenuContainer):
    def __init__(self,menu_options_and_associated_nodes:list[MenuOption],child_pageination:int=10):
        labels=list(i.label.format(len(i.nodes)) for i in menu_options_and_associated_nodes)
        self.child_nodes=list(i.nodes for i in menu_options_and_associated_nodes)
        self.options_for_menu=[Option(value=str(i),label=labels[i]) for i in range(len(labels))]
        self.child_pageination=child_pageination
    def format_container(self, rootkey:str,pointer_to_container:ExpandPointer, child_already_selected:int=-1) -> InteractiveElement:
        if child_already_selected == -1: #not already selected
            return RadioButtonsElement(action_id=TreeNodeUI._serialize_callback(rootkey,pointer_to_container),options=self.options_for_menu)
        else: #one of the options already selected
            return RadioButtonsElement(action_id=TreeNodeUI._serialize_callback(rootkey,pointer_to_container),
                                       initial_option=self.options_for_menu[child_already_selected],
                                       options=self.options_for_menu)
