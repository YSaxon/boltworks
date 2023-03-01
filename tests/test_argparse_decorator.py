from __future__ import annotations
# pylint: disable=redefined-outer-name

import argparse
import inspect
from typing import Callable, List
from unittest import mock

from slack_bolt import Args
from boltworks import argparse_command
import pytest

from tests.common import mock_an_args







def test_argparsing():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--a", nargs="*", type=float)
    argparser.add_argument("-b", type=int)
    argparser.add_argument("c")
    argparser.add_argument("d", nargs="?", default="default")
    
    closure_vars = {}

    @argparse_command(argparser)
    def command_handler(args:Args, a, b, c, d):
        closure_vars["a"] = a
        closure_vars["b"] = b
        closure_vars["c"] = c
        closure_vars["d"] = d


    args,respond,say=mock_an_args()
    args.command=dict(command="/test", text="3 --a 1 1.5 -b 2")

    command_handler(args=args)
    
    assert closure_vars["a"] == [1.0, 1.5]
    assert closure_vars["b"] == 2
    assert closure_vars["c"] == "3"
    assert closure_vars["d"] == "default"
    
    
def test_argparse_vars_passed_to_slack():

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--a", nargs="*", type=float)
    argparser.add_argument("-b", type=int)
    argparser.add_argument("c")
    argparser.add_argument("d", nargs="?", default="default")
    
    @argparse_command(argparser)
    def command_handler(args, a, logger, b, c, respond, d):...
    
    argspec = inspect.getfullargspec(command_handler).args
    assert argspec==["args"] #only thing that should actually get passed to slack is the args param from which we will parse the others

def test_all_slackvars_passed_through():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("a", type=int)
    argparser.add_argument("b", type=int)
    argparser.add_argument("c", type=int)
    argparser.add_argument("d", type=int)
    
    
    args,respond,say=mock_an_args()
    closure_args=args
    command=dict(command="/test", text="1 2 3 4")
    args.command=command
    
    @argparse_command(argparser)
    def command_handler(args:Args, a, say, b, command, c, respond, d):
        assert a==1
        assert b==2
        assert c==3
        assert d==4
        
        assert say is args.say is closure_args.say
        assert respond is args.respond is closure_args.respond
        assert command is args.command is closure_args.command
    
    command_handler(args=args)
    



def test_argparsing_automagic_simple():
    @argparse_command(automagic=True)
    def command_handler(args:Args, i:int):
        args.respond(str(i))

    args,respond,say=mock_an_args()
    

    args.command=dict(command="/test", text="1")
    
    command_handler(args=args)
    
    respond.assert_called_once_with("1")


def test_argparsing_automagic_defaultval_filled():
    @argparse_command(automagic=True)
    def command_handler(args:Args, i=5):
        args.respond(str(i))

    args,respond,say=mock_an_args()
    

    args.command=dict(command="/test", text="1")
    
    command_handler(args=args)
    
    respond.assert_called_once_with("1")
    
def test_argparsing_automagic_defaultval_unfilled():
    @argparse_command(automagic=True)
    def command_handler(args:Args, i=5):
        args.respond(str(i))

    args,respond,say=mock_an_args()
    

    args.command=dict(command="/test", text="")
    
    command_handler(args=args)
    
    respond.assert_called_once_with("5")
    
    
def test_argparsing_automagic_requiredlistval_filled():
    @argparse_command(automagic=True)
    def command_handler(args:Args, i:list[int]):
        args.respond(str(i[1]))

    args,respond,say=mock_an_args()
    

    args.command=dict(command="/test", text="2 6")
    
    command_handler(args=args)
    
    respond.assert_called_once_with("6")
    
    
def test_argparsing_automagic_required_defaultlistval_filled():
    @argparse_command(automagic=True)
    def command_handler(args:Args, i:list[int]=[5,3]):
        args.respond(str(i[1]))

    args,respond,say=mock_an_args()
    

    args.command=dict(command="/test", text="2 6")
    
    command_handler(args=args)
    
    respond.assert_called_once_with("6")
    
def test_argparsing_automagic_required_defaultlistval_filled():
    @argparse_command(automagic=True)
    def command_handler(args:Args, i:list[int]):
        args.respond(str(i[1]))

    args,respond,say=mock_an_args()
    

    args.command=dict(command="/test", text="2 6")
    
    command_handler(args=args)
    
    respond.assert_called_once_with("6")
    
def test_argparsing_automagic_defaultlistval_unfilled():
    @argparse_command(automagic=True)
    def command_handler(args:Args, i:list[int]=[5,3]):
        args.respond(str(i[1]))

    args,respond,say=mock_an_args()

    args.command=dict(command="/test", text="")
    
    command_handler(args=args)
    
    respond.assert_called_once_with("3")
    
    
def test_argparsing_automagic_defaultlistval_unfilled():
    @argparse_command(automagic=True)
    def command_handler(args:Args, i:list[int]=[5,3]):
        args.respond(str(i[1]))

    args,respond,say=mock_an_args()
    
    args.command=dict(command="/test", text="")
    
    command_handler(args=args)
    
    respond.assert_called_once_with("3")
    
    
def test_argparsing_automagic_multiple():
        
    closure_vars={}
    
    @argparse_command(automagic=True)
    
    def command_handler(args:Args, a: List[float], b: int, c: str):
        closure_vars["a"] = a
        closure_vars["b"] = b
        closure_vars["c"] = c
    args,respond,say=mock_an_args()
    

    args.command=dict(command="/test", text="3 1.5 2 5")
    # args.command=dict(command="/test", text="--c 3 --a 1 1.5 --b 2")
    
    command_handler(args=args)
    
    assert closure_vars["a"] == [3, 1.5]
    assert closure_vars["b"] == 2
    assert closure_vars["c"] == "5"
    
    
def test_argparsing_automagic_multiple_kwarg_only():
        
    closure_vars={}
    
    @argparse_command(automagic=True)
    def command_handler(args:Args, *, a: List[float], b: int, c: str):
        closure_vars["a"] = a
        closure_vars["b"] = b
        closure_vars["c"] = c
    args,respond,say=mock_an_args()
    

    args.command=dict(command="/test", text="--a 3 1.5 --b 2 --c 5")
    
    command_handler(args=args)
    
    assert closure_vars["a"] == [3, 1.5]
    assert closure_vars["b"] == 2
    assert closure_vars["c"] == "5"
    
    
def test_automagic_vars_passed_to_slack():

    @argparse_command(automagic=True)
    def command_handler(args, a:int, logger, b:int, c:int, respond, d:int):...
    
    argspec = inspect.getfullargspec(command_handler).args
    assert argspec==["args"] #only thing that should actually get passed to slack is the args param from which we will parse the others

def test_automagic_all_slackvars_passed_through():
    
    args,closure_respond,closure_say=mock_an_args()
    closure_args=args
    closure_command=dict(command="/test", text="1 2 3 4")
    args.command=closure_command
    
    @argparse_command(automagic=True)
    def command_handler(args, a:int, command, b:int, respond, c:int, say, d:int):
        assert a==1
        assert b==2
        assert c==3
        assert d==4
        
        assert say is args.say is closure_args.say is closure_say
        assert respond is args.respond is closure_args.respond is closure_respond
        assert command is args.command is closure_args.command is closure_command
    
    command_handler(args=args)
    
def test_argparsing_with_no_slackargs():
    """Sample pytest test function with the pytest fixture as an argument."""
    
    closure_var=[]
    
    @argparse_command(automagic=True)
    def command_handler(i:int):
        closure_var.append(i)

    args,respond,say=mock_an_args()
    
    args.command=dict(command="/test", text="1")
    
    command_handler(args=args)
    
    assert closure_var==[1]
    
    
    
def test_argparsing_with_individual_slack_args():
    """Sample pytest test function with the pytest fixture as an argument."""
    @argparse_command(automagic=True)
    def command_handler(respond, i:int):
        respond(str(i))

    args,respond,say=mock_an_args()
    

    args.command=dict(command="/test", text="1")
    
    command_handler(args=args)
    
    respond.assert_called_once_with("1")
    

def test_argparsing_automagic_simple_with_individual_slack_args():
    """Sample pytest test function with the pytest fixture as an argument."""
    @argparse_command(automagic=True)
    def command_handler(respond, i:int):
        respond(str(i))

    args,respond,say=mock_an_args()
    

    args.command=dict(command="/test", text="1")
    
    command_handler(args=args)
    
    respond.assert_called_once_with("1")