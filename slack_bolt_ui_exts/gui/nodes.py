from __future__ import annotations

import datetime
import re
from functools import partial
from typing import Iterable, Optional, Protocol, Tuple, Union, overload
from uuid import uuid1

from expiringdict import ExpiringDict
from helper.kvstore import KVStore
from more_itertools import chunked
from pydantic import BaseModel
from slack_bolt.app import App
from slack_bolt_ui_exts.gui.containers import (ButtonChildContainer,
                                               ChildNodeContainer,
                                               ChildNodeMenuContainer)
from slack_bolt_ui_exts.gui.expandpointer import ExpandPointer
from slack_sdk.models.blocks import (ActionsBlock, Block, ButtonElement,
                                     ContextBlock, InteractiveElement,
                                     OverflowMenuElement, RadioButtonsElement,
                                     SectionBlock, StaticSelectElement)
from slack_sdk.models.blocks.block_elements import MarkdownTextObject, Option
from slack_sdk.web.slack_response import SlackResponse
from slack_sdk.webhook import WebhookResponse
from utils import simple_slack_block

NAMELESS_FMT_STR_EXPAND="expand {}"
NAMELESS_FMT_STR_COLLAPSE="collapse {}"



class TreeNode:
    """The basic building block of this UI library, a Node has it's own Blocks, under formatblocks, and optionally, one or more child_containers containing one or more child nodes which can be expanded
    If there is only one childNodeContainer it will by default be placed on the side of the first formatblock
    If there is more than one, they will by default be placed on their own row, after the formatblocks
    This behavior can be overriden with the `first_child_container_on_side` param
    """
    def __init__(
        self,
        formatblocks:Union[list[Block],Block,str],
        children_containers:ChildNodeContainer|ChildNodeMenuContainer|list[ChildNodeContainer|ChildNodeMenuContainer]=[],
        first_child_container_on_side:bool=None,
        auto_expand_children_if_only_one=False):
        """_summary_

        Args:
            formatblocks (Union[list[Block],Block,str]): The formatting blocks for the node
            children_containers (ChildNodeContainer | ChildNodeMenuContainer | list[ChildNodeContainer | ChildNodeMenuContainer], optional): The whole point of the UI: these are interactive elements which if clicked/selected, will expand their child nodes underneath the node
            first_child_container_on_side (bool, optional): This overrides the default behavior, which is to put the first childNodeContainer on the side of the first formatting block IF it is the only childNodeContainer
            auto_expand_children_if_only_one (bool, optional): This option is deprecated and may be removed. It forces expand for any child that itself only has a single child node. Defaults to False.
        """
        self.formatblocks=formatblocks
        self.children_containers=children_containers if isinstance(children_containers,list) else [children_containers]
        if first_child_container_on_side is not None:
            self.first_child_container_on_side=first_child_container_on_side # override
        else: self.first_child_container_on_side = len(self.children_containers)==1 # default behavior for side placement
        self.auto_expand_children_if_only_one=auto_expand_children_if_only_one #delete?
    def __repr__(self):
        toreturn=f"{type(self)} "
        if self.children_containers:
            toreturn+=f"({len(self.children_containers)} children_containers, total grandchildren_nodes {sum(len(cc.child_nodes) for cc in self.children_containers)}) "
        toreturn+=": "
        if isinstance(self.formatblocks,str): toreturn+=self.formatblocks
        elif isinstance(self.formatblocks,SectionBlock): toreturn+=self.formatblocks.text.text
        elif isinstance(self.formatblocks,list): toreturn+="\n".join([b.text.text if isinstance(b,SectionBlock) and b.text else b.to_dict() for b in self.formatblocks])
        return toreturn

    def text_formatting_as_str(n): #best try basis, not guaranteed to return correctly
        if isinstance(n.formatblocks,str): return n.formatblocks
        elif isinstance(n.formatblocks,SectionBlock): return n.formatblocks.text.text
        elif isinstance(n.formatblocks,list): return "\n".join([fb.text.text for fb in n.formatblocks if 'text' in fb.attributes])
        else: return "" #or raise exception??

    def __setstate__(self, state): #necessary only in transitional period to allow depickling older treenodes
        self.__dict__.update(state)
        children_containers=state["children_containers"] if "children_containers" in state else []
        if "children" in state and state["children"]:
            children_containers.append(ButtonChildContainer(state["children"],state["expand_button_format_string"],state["collapse_button_format_string"]))
            #and maybe just add an exception handler that if someone selects something invalid will make sure it refreshes anyway, and then whatever existing buttons there are will automatically be readdressed correctly
        if "button_pane_children" in state and state["button_pane_children"]:
            children_containers.extend(ButtonChildContainer(bpc.treenodes,static_button_text=bpc.button_text) for bpc in state["button_pane_children"])
        if not "first_child_container_on_side" in state: self.__dict__["first_child_container_on_side"]=len(children_containers)==1
        self.__dict__["children_containers"]=children_containers

    @staticmethod
    def withSimpleSideButton(formatblocks:Union[list[Block],Block,str],children:list[TreeNode]=[],expand_button_format_string:str=NAMELESS_FMT_STR_EXPAND,collapse_button_format_string:str=NAMELESS_FMT_STR_COLLAPSE,child_pageination:int=10)->TreeNode:
        """A simple way to get a basic node with a side button expanding its children

        Args:
            formatblocks (Union[list[Block],Block,str]): the formatting blocks for the node itself
            children (list[TreeNode], optional): any children for the node
            expand_button_format_string (str, optional): a string for the side button if any, when it is not yet expanded, if {} is in the string, it will be replaced with the number of children
            collapse_button_format_string (str, optional):  a string for the side button if any, when it is already expanded, if {} is in the string, it will be replaced with the number of children
            child_pageination (int, optional): _description_. Defaults to 10.

        Returns:
            TreeNode: the treenode requested
        """
        return TreeNode(formatblocks,[ButtonChildContainer(children,expand_button_format_string,collapse_button_format_string,child_pageination=child_pageination)] if children else [])

    @staticmethod
    def fromJson(formatblocks:Union[str,Block,list[Block]],jsonlike:Union[list,dict],pageination=15,optimize_blocks=True):
        return TreeNode(formatblocks,[ButtonChildContainer.forJsonDetails(jsonlike,"details",pageination,optimize_blocks)])
