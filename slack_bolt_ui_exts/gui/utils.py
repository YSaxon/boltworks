from __future__ import annotations

from nodes import NAMELESS_FMT_STR_COLLAPSE, NAMELESS_FMT_STR_EXPAND, TreeNode
from pydantic import BaseModel
from slack_sdk.models.blocks import SectionBlock


def simple_slack_block(text:str):
    if len(text) >= 3000: #in the unlikely that this single block is too big by itself, truncate it
        text=text[:2845] + ' \n_..(this block was truncated due to slack limits).._'
    if not text: text = " " #bugfix, an empty string results in an illegal block
    return SectionBlock(text=text)

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
            if isinstance(n.formatblocks,SectionBlock): n.formatblocks=n.formatblocks.text.text #convert it to using strings
            elif isinstance(n.formatblocks,list) and isinstance(n.formatblocks[0],SectionBlock): n.formatblocks=n.formatblocks[0].text.text

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
    if not isinstance(object,(list,dict,BaseModel)): #this needs to be in here rather than the containing function for the recursion
        return f"{prefix}{object}"

    if isinstance(object,list): #convert other types to dict, could add other container types here if neccesary
        object={f"[{x}]":y for x,y in enumerate(object,1)} if len(object)<10 \
          else {f"[{x:2}]":y for x,y in enumerate(object,1)} #format with a space for neatness if len>10

    elif isinstance(object,BaseModel):
        object=object.dict()

    if inline_child_if_solo and len(object)==1: #if we have only one, then just print it inline
        key,value=object.popitem()
        return _convert_jsonlike_to_dict(prefix=f"{prefix}{key}: ",object=value,inline_child_if_solo=True)

    return {f"{prefix}{k}":v for k,v in object.items()}
