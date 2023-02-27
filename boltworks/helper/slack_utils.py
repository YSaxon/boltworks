from __future__ import annotations

import textwrap
from typing import Callable
from slack_sdk.models.blocks import SectionBlock

def simple_slack_block(text:str):
    if len(text) >= 3000: #in the unlikely that this single block is too big by itself, truncate it
        text=text[:2845] + ' \n_..(this block was truncated due to slack limits).._'
    if not text: text = " " #bugfix, an empty string results in an illegal block
    return SectionBlock(text=text)

def safe_post_in_blockquotes(chatpostmethod:Callable,*args,**kwargs):
    if "blocks" in kwargs:
        return chatpostmethod(*args,**kwargs)#just post it
    if not "text" in kwargs:
        if not args:
            #forget it just post as is
            return chatpostmethod(*args,**kwargs)
        else:
            text:str=args[0]
            def post(topost): return chatpostmethod(topost,*args[1:], **kwargs)
    else:
        text=kwargs["text"]
        nontextkwargs={k:v for k,v in kwargs.items() if k !="text"}
        def post(topost): return chatpostmethod(*args, text=topost,**nontextkwargs)
    if len(text)<=3994:
        return post(f"```{text}```")
    _post_lines_quoted(text.splitlines(), post)

def _post_lines_quoted(lines:list[str], post:Callable):
    while lines:
        if len(lines[0])>3990:#if a single line is too long all by itself, which would cause an endless loop
            _post_lines_quoted(textwrap.wrap(lines.pop(0),width=1000),post) #alternatively could inline this by popping the line, applying wrap, and then inserting the results into the list again at 0 and hitting continue to restart
        chunk="```\n"
        while lines:
            if len(chunk)+len(lines[0])<=3996:
                chunk+= lines.pop(0)+"\n"
            else:
                break
        chunk+="```"
        post(chunk)
