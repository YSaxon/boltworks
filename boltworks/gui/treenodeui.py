from __future__ import annotations

import datetime
import re
from typing import Iterable, Optional, Tuple, Union, overload
from uuid import uuid1
from expiringdict import ExpiringDict
from more_itertools import chunked
from slack_bolt import Respond, Say
from slack_bolt.app import App
from slack_sdk.models.blocks import (ActionsBlock, Block, ButtonElement,
                                     ContextBlock, InteractiveElement,
                                     OverflowMenuElement, RadioButtonsElement,
                                     SectionBlock, StaticSelectElement)
from slack_sdk.models.blocks.block_elements import MarkdownTextObject, Option
from slack_sdk.webhook import WebhookResponse
from boltworks.boltworks.gui.expandpointer import ExpandPointer
from boltworks.boltworks.helper.kvstore import KVStore
from static_utils.slack_block_utils import simple_slack_block

NAMELESS_FMT_STR_EXPAND="expand {}"
NAMELESS_FMT_STR_COLLAPSE="collapse {}"



            

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
        return response
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
                blocks[0].accessory=format_nth_container(0) # type: ignore
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
    
    


class TreeNode:
    """The basic building block of this UI library, a Node has it's own Blocks, under formatblocks, and optionally, one or more child_containers containing one or more child nodes which can be expanded
    If there is only one childNodeContainer it will by default be placed on the side of the first formatblock
    If there is more than one, they will by default be placed on their own row, after the formatblocks
    This behavior can be overriden with the `first_child_container_on_side` param
    """
    def __init__(
        self,
        formatblocks:Union[list[Block],Block,str],
        children_containers:ChildNodeContainer|ChildNodeMenuContainer|list[ChildNodeContainer|ChildNodeMenuContainer]|None=None,
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
        self.children_containers=children_containers if isinstance(children_containers,list) else [children_containers] if children_containers else []
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


class ChildNodeContainer:
    child_nodes:list[TreeNode]
    child_pageination:int=10
    def format_container(self,rootkey:str,pointer_to_container:ExpandPointer,child_already_selected:int=-1)->InteractiveElement:...

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


class MenuOption:
    def __init__(self,label:str,nodes:list[TreeNode]):
        self.label=label
        self.nodes=nodes
    @staticmethod
    def fromJson(label:str,json:list|dict,pageination=15,optimize_blocks=True):
        children,numchildren=_jsonlike_to_treenode_and_truenum_children(json,pageination=pageination,optimize_blocks=optimize_blocks)
        return MenuOption(label.format(numchildren),children)

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
                                    options=[Option(value=str(-1),label=" "), *self.options_for_menu]) #-1 to contract all, space to be a valid label

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







def _jsonlike_to_treenode_and_truenum_children(object,pageination:int=15,optimize_blocks:bool=True,name:str="",_level:int=0):
    indent="•"*_level
    object = _convert_jsonlike_to_dict(object,inline_child_if_solo=_level>0)
    if not isinstance(object,dict):                                                                 #just a simple key value pair        > key: value
        return TreeNode([simple_slack_block(f"{indent} {name}: {object}")]),0                       #add a line with an expand button    > key: [expand button]

    children=[_jsonlike_to_treenode_and_truenum_children(name=key,object=value,optimize_blocks=optimize_blocks,_level=_level+1)[0]
                        for key,value in object.items()
                        if value or value==False]#we only want to exclude falsy/empty things, not False or 0 which both == False
    num_children_preoptimization=len(children)
    children=slack_block_optimize_treenode(children) if optimize_blocks else children
    if _level>0:
        return TreeNode.withSimpleSideButton([simple_slack_block(f"{indent} {name}")], #TODO?maybe add some kind of preview with something like {str(object)[5]}..., but would need to calculate the total width of field
                    children=children,
                    expand_button_format_string=NAMELESS_FMT_STR_EXPAND.format(num_children_preoptimization),
                    collapse_button_format_string=NAMELESS_FMT_STR_COLLAPSE.format(num_children_preoptimization),
                    child_pageination=pageination),num_children_preoptimization
    return children,num_children_preoptimization

def slack_block_optimize_treenode(children:list[TreeNode])->list[TreeNode]:
    """This method will try to reduce the number of formatting blocks used by a list of Treenode, to fit more blocks without pageinating or going over the slack limit of 50

    Args:
        children (list[TreeNode]): the nodes to optimize

    Returns:
        list[TreeNode]: a fewer number of nodes, with some adjacent ones combined
    """
    if not children: return []
    out_children = []
    combined_node_buffer = None #will always be either None or a TreeNode with a str as formattingblocks
    for n in children:
        if not _is_simple_text_block(n) or n.children_containers: #if the nodes have complicated blocks or children
            if combined_node_buffer:
                out_children.append(combined_node_buffer) #then just flush the buffer
                combined_node_buffer=None
            out_children.append(n)                        #and append this node

        else: #a simple terminal block that we can combine with other ones to optimize block count:
            if isinstance(n.formatblocks,SectionBlock): n.formatblocks=n.formatblocks.text.text if n.formatblocks.text else '' #convert it to using strings
            elif isinstance(n.formatblocks,list) and isinstance(n.formatblocks[0],SectionBlock): n.formatblocks=n.formatblocks[0].text.text if n.formatblocks[0].text else ''

            if not combined_node_buffer:       #if no buffer, just start one
                combined_node_buffer=n
            else:                       #otherwise add the string to existing combined_tn, assuming it fits in char limits
                if len(combined_node_buffer.formatblocks)+len(n.formatblocks)+2 < 3000:#slack char limits for a single section block
                    combined_node_buffer.formatblocks+="\n\n"+n.formatblocks

                else: #if would be over char limits, we have no choice but to flush the buffer and restart
                    if combined_node_buffer: out_children.append(combined_node_buffer)
                    combined_node_buffer=n #set this block as new buffer

    if combined_node_buffer: out_children.append(combined_node_buffer) #flush the buffer one last time
    return out_children


def _is_simple_text_block(n:TreeNode):
    return isinstance(n.formatblocks,str) \
        or isinstance(n.formatblocks,SectionBlock) and not n.formatblocks.accessory and not n.formatblocks.fields \
        or isinstance(n.formatblocks,list) and len(n.formatblocks)==1 and isinstance(n.formatblocks[0],SectionBlock) and not n.formatblocks[0].accessory and not n.formatblocks[0].fields


def _convert_jsonlike_to_dict(object,prefix="",inline_child_if_solo:bool=True):
    if not isinstance(object,(list,dict)):#,'BaseModel')): #this needs to be in here rather than the containing function for the recursion
        return f"{prefix}{object}"

    if isinstance(object,list): #convert other types to dict, could add other container types here if neccesary
        object={f"[{x}]":y for x,y in enumerate(object,1)} if len(object)<10 \
          else {f"[{x:2}]":y for x,y in enumerate(object,1)} #format with a space for neatness if len>10

    # elif isinstance(object,BaseModel):
    #     object=object.dict()

    if inline_child_if_solo and len(object)==1: #if we have only one, then just print it inline
        key,value=object.popitem()
        return _convert_jsonlike_to_dict(prefix=f"{prefix}{key}: ",object=value,inline_child_if_solo=True)

    return {f"{prefix}{k}":v for k,v in object.items()}