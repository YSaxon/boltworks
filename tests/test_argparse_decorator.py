#!/usr/bin/env python
"""Tests for `slack_bolt_ui_exts` package."""
# pylint: disable=redefined-outer-name

import argparse
import inspect
from typing import List
from unittest import mock

import pytest
from slack_bolt_ui_exts.commands.decorator import argparse_command


@pytest.fixture
def fixtures():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--a", nargs="*", type=float)
    argparser.add_argument("-b", type=int)
    argparser.add_argument("c")
    argparser.add_argument("d", nargs="?", default="default")

    record_vars = {}

    @argparse_command(argparser)
    def command_handler(logger, say, a, b, c, d):
        record_vars["a"] = a
        record_vars["b"] = b
        record_vars["c"] = c
        record_vars["d"] = d

    return command_handler, record_vars


def test_argparse_vars_passed_to_slack(fixtures):
    """Sample pytest test function with the pytest fixture as an argument."""
    command_handler, record_vars = fixtures

    args = inspect.getfullargspec(command_handler).args
    assert "logger" in args
    assert "a" not in args  # that shouldn't get passed to slack

    del command_handler, record_vars, fixtures


def test_argparsing(fixtures):
    """Sample pytest test function with the pytest fixture as an argument."""
    command_handler, record_vars = fixtures

    command_handler(
        command=dict(command="/test", text="3 --a 1 1.5 -b 2"),
        context=dict(user_id="testuserid"),
        say=mock.Mock(),
        logger=mock.Mock(),
        respond=mock.Mock(),
        ack=mock.Mock(),
    )
    assert record_vars["a"] == [1.0, 1.5]
    assert record_vars["b"] == 2
    assert record_vars["c"] == "3"
    assert record_vars["d"] == "default"

    del command_handler, record_vars, fixtures


@pytest.fixture
def automagic():
    argparser = argparse.ArgumentParser()
    record_vars = {}

    @argparse_command(argparser, automagic=True)
    def command_handler(logger, say, a: List[float], b: int, c: str, d="default"):
        record_vars["a"] = a
        record_vars["b"] = b
        record_vars["c"] = c
        record_vars["d"] = d

    return command_handler, record_vars


def test_argparse_vars_passed_to_slack_automagic(automagic):
    """Sample pytest test function with the pytest fixture as an argument."""
    command_handler, record_vars = automagic

    args = inspect.getfullargspec(command_handler).args
    assert "logger" in args
    assert "a" not in args  # that shouldn't get passed to slack

    del command_handler, record_vars, automagic


def test_argparsing_automagic(automagic):
    """Sample pytest test function with the pytest fixture as an argument."""
    command_handler, record_vars = automagic

    command_handler(
        command=dict(command="/test", text="--c 3 --a 1 1.5 --b 2"),
        context=dict(user_id="testuserid"),
        say=mock.Mock(),
        logger=mock.Mock(),
        respond=mock.Mock(),
        ack=mock.Mock(),
    )
    assert record_vars["a"] == [1.0, 1.5]
    assert record_vars["b"] == 2
    assert record_vars["c"] == "3"
    assert record_vars["d"] == "default"

    del command_handler, record_vars, automagic
