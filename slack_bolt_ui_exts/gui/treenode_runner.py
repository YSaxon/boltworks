
from __future__ import annotations

import datetime
import re
from functools import partial
from typing import Optional, Protocol, Tuple, Union
from uuid import uuid1

from expiringdict import ExpiringDict
from helper.kvstore import KVStore
from more_itertools import chunked
from slack_bolt import Respond, Say
from slack_bolt.app import App
from slack_bolt_ui_exts.gui.containers import (ChildNodeContainer,
                                               ChildNodeMenuContainer)
from slack_bolt_ui_exts.gui.expandpointer import ExpandPointer
from slack_bolt_ui_exts.gui.nodes import TreeNode
from slack_sdk.models.blocks import (ActionsBlock, Block, ButtonElement,
                                     ContextBlock)
from slack_sdk.models.blocks.block_elements import MarkdownTextObject
from slack_sdk.web.slack_response import SlackResponse
from slack_sdk.webhook import WebhookResponse
from utils import simple_slack_block

prefix_for_callback="tn@"
class TreeNodeUI:
    def __init__(self,app:App,kvstore:KVStore) -> None:
        """This is the managing class for the NodeUI, which handles posting nodes and then responding to InteractiveElements to expand/contract node children

        Args:
            app (App): A Slack Bolt App instance, for posting and registering actionhandlers
            kvstore (_type_): a KVStore instance, for storing and looking up Nodes
        """
        app.action(re.compile(f"{prefix_for_callback}.*"))(self._do_callback_action)
        self.expiring_root_dict=ExpiringDict(max_age_seconds=120,max_len=20)
        self.kvstore=kvstore #.namespaced(prefix_for_callback)
        self._slack_chat_client=app.client

    def post_single_node(self,post_callable_or_channel:str|Say|Respond,node:TreeNode,alt_text:str=None,expand_first:bool=False):
        """Posts a Single Node
        Args:
            post_callable_or_channel: either an instance of Respond or Say, or a channelid to post to
            node (TreeNode): the node to post
            alt_text (str, optional): for notifications that require a simple string
            expand_first (bool, optional): if set to True, the Node will post with its first child container expanded [to its first menu option]
        """
        say=Say(self._slack_chat_client,post_callable_or_channel) if isinstance(post_callable_or_channel,str) else post_callable_or_channel
        rootkey=self._rootkey_from_treenode(node)
        return say(text=alt_text or node.text_formatting_as_str(),
                                 blocks=self._format_tree(rootkey,expand_first=expand_first),unfurl_links=False)

    def post_treenodes(self,post_callable_or_channel:str|Say|Respond,treenodes:list[TreeNode],post_all_together:bool,global_header:str=None,*,message_if_none:str=None,expand_first_if_seperate=False,**other_global_tn_kwargs):
        """Posts multiple Nodes together

        Args:
            post_callable_or_channel (Union[PostMethod,str]): either an instance of Respond or Say, or a channelid to post to
            treenodes (list[TreeNode]): the nodes to post
            post_all_together (bool): if True, will collect the nodes under a parent node so they can all be collapsed together to save space
            global_header (str, optional): if posting together, this will be the text of the parent node, otherwise just a header posted before the nodes
            message_if_none (str, optional): optionally, provide a string to post if there are no nodes
            expand_first_if_seperate (bool, optional): like expand_first for post_single_node, only effective if posting the blocks seperately
        """
        say=Say(self._slack_chat_client,post_callable_or_channel) if isinstance(post_callable_or_channel,str) else post_callable_or_channel
        if not treenodes:
            if message_if_none: say(message_if_none)
            return
        if post_all_together:
            num_treenodes=f" ({len(treenodes)}) " if len(treenodes)>1 else ""
            alt_text=f"{global_header}: {num_treenodes} {treenodes[0].text_formatting_as_str()} "
            say(text=alt_text,
                blocks=self._format_tree(
                    self._rootkey_from_treenode(TreeNode.withSimpleSideButton(
                    formatblocks=global_header if global_header else [],
                    children=treenodes,
                    **other_global_tn_kwargs
                )),expand_first=True
            ),unfurl_links=False)
        else:
            if global_header:
                say(text=global_header)
            for node in treenodes:
                rootkey=self._rootkey_from_treenode(node)
                alt_text=node.text_formatting_as_str()
                say(text=alt_text,blocks=self._format_tree(rootkey,expand_first=expand_first_if_seperate),unfurl_links=False)

    def _rootkey_from_treenode(self,node:TreeNode):
        rootkey=str(uuid1())
        self.kvstore[rootkey]=node
        self.expiring_root_dict[rootkey]=node
        return rootkey

    def _get_root(self,rootkey:str)->TreeNode:
        if rootkey in self.expiring_root_dict:
            return self.expiring_root_dict[rootkey]
        root=self.kvstore[rootkey]
        self.expiring_root_dict[rootkey]=root
        return root

    def _do_callback_action(self,ack,action,respond):
        # if logging.root.level<=logging.DEBUG:
        #     self.profiler.start()
        ack()#find a way of threading that maybe?
        callback_data=action['action_id'][len(prefix_for_callback):]
        rootkey,expandpointer=self._deserialize_callback(callback_data)
        value = action['selected_option']['value'] if 'selected_option' in action and 'value' in action['selected_option'] else None
        if value:
            if int(value) == -1: #deselect
                expandpointer=expandpointer[:-1]
            else:
                expandpointer=expandpointer.extend([int(value),0])
        blocks=self._format_tree(rootkey,expandpointer=expandpointer)
        response=respond(replace_original=True,blocks=blocks)
        if isinstance(response, WebhookResponse):
            if response.status_code!=200:
                respond(f"error in slack handling: {response.body}",replace_original=False)
                print(f"{datetime.datetime.now()}: error in slack handling: {response.body}")
        # if logging.root.level<=logging.DEBUG:
        #     self.profiler.stop()
        #     print(self.profiler.output_text(unicode=True, color=True))

    @staticmethod
    def _button_to_replace_block(button_text:str,rootkey:str,expandpointer:ExpandPointer,**format_options):
        serialized_data=TreeNodeUI._serialize_callback(rootkey,expandpointer)
        button=ButtonElement(
            text=button_text,
            action_id=f"{serialized_data}",
            **format_options
        )
        return button

    @staticmethod
    def _serialize_callback(rootkey:str,expandpointer:ExpandPointer)->str:
        serialized_pointer=','.join([str(v) for v in expandpointer])
        return f"{prefix_for_callback}{rootkey}^{serialized_pointer}"

    @staticmethod
    def _deserialize_callback(data:str)->Tuple[str,ExpandPointer]:
        rootkey,serialized_pointer=data.rsplit('^', 1)
        pointerelems=serialized_pointer.split(',')
        expandpointer=ExpandPointer([int(p) for p in pointerelems])
        return rootkey,expandpointer

    def _format_tree(self,rootkey:str,*,expandpointer:ExpandPointer=ExpandPointer([0]),expand_first=False):
        root=self._get_root(rootkey)
        if expand_first and root.children_containers:
            if isinstance(root.children_containers[0],ChildNodeContainer):
                expandpointer=ExpandPointer([0,0,0])
            elif isinstance(root.children_containers[0],ChildNodeMenuContainer):
                expandpointer=ExpandPointer([0,0,0,0])
        diminish_pageination_by=0
        blocks_to_return =  self._format_tree_recursive(
                        parentnodes=[root],
                        expandpointer=expandpointer,
                        ancestral_pointer=ExpandPointer([]),
                        rootkey=rootkey,
                        parents_pagination=1,
                        diminish_pageination_by=0
                    )
        if len(blocks_to_return)>50:#this could probably be made more efficient, but for now, this should suffice
            while len(blocks_to_return)>49:
                diminish_pageination_by+=1
                blocks_to_return =  self._format_tree_recursive(
                            parentnodes=[root],
                            expandpointer=expandpointer,
                            ancestral_pointer=ExpandPointer([]),
                            rootkey=rootkey,
                            parents_pagination=1,
                            diminish_pageination_by=diminish_pageination_by
                        )
            blocks_to_return.append(ContextBlock(elements=[MarkdownTextObject(text="(blocks were repaginated to avoid exceeding slack limits)")]))
        return blocks_to_return

    def _format_tree_recursive(self,
                    parentnodes:list[TreeNode],
                    expandpointer:ExpandPointer,#:list[int], #could just make last one the start_at pointer and only go deeper if theres more
                    ancestral_pointer:ExpandPointer,
                    rootkey:str,
                    parents_pagination:int=10,
                    diminish_pageination_by=0 #in case we exceed block limits, we can retry with some number here to recursively diminish the pageination
                )->list[Block]:
                parents_pagination=parents_pagination if not diminish_pageination_by else max(1,parents_pagination-diminish_pageination_by)
                child_insert,remaining_expandpointer=expandpointer[0],expandpointer[1:]
                num_parents=len(parentnodes)
                start_at=self._startat(child_insert,parents_pagination)
                end_at=self._endat(start_at,parents_pagination,num_parents)
                blocks:list[Block]=[]
                before_blocks=[blocks for number,node in enumerate(parentnodes[start_at:child_insert],start_at) for blocks in self._formatblock(node,ancestral_pointer.append(number),rootkey)]
                blocks.extend(before_blocks)
                blocks_for_pointed_node=self._formatblock(parentnodes[child_insert],ancestral_pointer.append(child_insert),rootkey,remaining_expandpointer)
                blocks.extend(blocks_for_pointed_node)
                if remaining_expandpointer:#if there are more nodes to expand in the pointer list
                    new_parent=parentnodes[child_insert]
                    children_containers=new_parent.children_containers
                    if remaining_expandpointer[0] > len(new_parent.children_containers):    #transitional
                        remaining_expandpointer=ExpandPointer([0,0])
                    if len(remaining_expandpointer)==1:                                     #transitional
                        remaining_expandpointer=ExpandPointer([0]).extend(remaining_expandpointer)
                    container_opened_index=remaining_expandpointer[0]
                    selected_container=children_containers[container_opened_index]
                    if isinstance(selected_container,ChildNodeContainer):
                        selected_container_blocks=self._format_tree_recursive(
                            parentnodes=selected_container.child_nodes if selected_container.child_nodes else [TreeNode("_(this pane is empty)_")],
                            parents_pagination=selected_container.child_pageination,
                            expandpointer=remaining_expandpointer[1:],
                            ancestral_pointer=ancestral_pointer.append(child_insert).append(remaining_expandpointer[0]),
                            rootkey=rootkey,
                            diminish_pageination_by=diminish_pageination_by
                            )
                    else: # isinstance(selected_container,ChildNodeContainerContainer):
                        selected_container_blocks=self._format_tree_recursive(
                            parentnodes=selected_container.child_nodes[remaining_expandpointer[1]] if selected_container.child_nodes and selected_container.child_nodes[remaining_expandpointer[1]] else [TreeNode("_(this pane is empty)_")],
                            parents_pagination=selected_container.child_pageination,
                            expandpointer=remaining_expandpointer[2:],#since this contains multiple lists of nodes, we need two pointer indexes to find the next node to show
                            ancestral_pointer=ancestral_pointer.append(child_insert).append(remaining_expandpointer[0]).append(remaining_expandpointer[1]),
                            rootkey=rootkey,
                            diminish_pageination_by=diminish_pageination_by
                            )
                    blocks.extend(selected_container_blocks)


                after_blocks= [blocks for number,node in enumerate(parentnodes[child_insert+1:end_at],child_insert+1) for blocks in self._formatblock(node,ancestral_pointer.append(number),rootkey)]
                blocks.extend(after_blocks)
                navig_blocks=self._make_prev_next_buttons(usePrev=start_at>0,useNext=end_at<num_parents,
                prev_callback=(rootkey,ancestral_pointer.append(start_at-parents_pagination if start_at-parents_pagination>0 else 0)),
                next_callback=(rootkey,ancestral_pointer.append(start_at+parents_pagination))) #if startat+parents_per_page<num_parents else 0
                if navig_blocks:
                    blocks.append(navig_blocks)
                return blocks

    def _formatblock(self,
                    node:TreeNode,
                pointer_to_block:ExpandPointer,
                rootkey:str,
                remaining_expandpointer:ExpandPointer=None):
        blocks:list[Block]=[]
        if isinstance(node.formatblocks,list):
            blocks.extend(node.formatblocks)
        elif isinstance(node.formatblocks,Block):
            blocks.append(node.formatblocks)
        elif isinstance(node.formatblocks,str) and node.formatblocks:
            blocks.append(simple_slack_block(node.formatblocks))

        def format_nth_container(n):
            if not remaining_expandpointer or remaining_expandpointer[0]!=n:
                return node.children_containers[n].format_container(rootkey,pointer_to_block.append(n),-1)
            else:
                child_selected=remaining_expandpointer[1] if isinstance(node.children_containers[n],ChildNodeMenuContainer) and len(remaining_expandpointer)>1 else 0
                return node.children_containers[n].format_container(rootkey,pointer_to_block.append(n),child_selected)

        if node.children_containers:
            if node.first_child_container_on_side and blocks and 'accessory' in blocks[0].attributes: #and not blocks[0].accessory
                blocks[0].accessory=format_nth_container(0)
                start_at=1
            else: start_at=0

            after_blocks_container_elements=(format_nth_container(n) for n in range(start_at,len(node.children_containers)))

            blocks.extend(ActionsBlock(elements=buttons_chunk) for buttons_chunk in chunked(after_blocks_container_elements,ActionsBlock.elements_max_length))

        return blocks

    def _make_prev_next_buttons(self,usePrev:bool,useNext:bool,prev_callback:Tuple[str,ExpandPointer],next_callback:Tuple[str,ExpandPointer])->Optional[ActionsBlock]:
        if (not usePrev) and (not useNext): return None
        buttons=[]
        if(usePrev): buttons.append(self._button_to_replace_block(":arrow_left:",*prev_callback))
        if(useNext): buttons.append(self._button_to_replace_block(":arrow_right:",*next_callback))
        navig_buttons=ActionsBlock(
            elements=buttons)
        return navig_buttons

    def _startat(self,value, pageinate):
        mod=value%pageinate
        return value-mod if value>=pageinate else 0


    def _endat(self,startat,pageinate,length):
        return startat+pageinate if startat+pageinate<length else length
