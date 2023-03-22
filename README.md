# Boltworks


![PyPI - Python Version](https://img.shields.io/pypi/pyversions/boltworks)
[![PyPI version](https://badge.fury.io/py/boltworks.svg)](https://badge.fury.io/py/boltworks)
[![codecov](https://codecov.io/gh/YSaxon/boltworks/branch/master/graph/badge.svg?token=MYK47OLRPF)](https://codecov.io/gh/YSaxon/boltworks)
![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/ysaxon/boltworks/dev.yml)
![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)


A collection of various extensions for Slack's bolt library to help you more easily make better slackbots.

[docs](https://ysaxon.github.io/boltworks/)

The main features are:
* Easy CLI parsing using the ArgParse library (or an automagic function parser that determines what params you need)
* Easy callbacks on buttons and other GUI elements
* A fast and flexible way of posting lots of information in a dynamically expandable GUI format


## Getting Started

```
pip install boltworks
```

Follow the instructions at https://github.com/slackapi/bolt-python to begin setting up a Slackbot. Note that BoltWorks is not presently designed for async use, but any of the non-async handlers should work. For testing purposes, socket mode tends to be the easiest.


## Easy CLIs with the @argparse_command decorator

[argparse_command in docs](https://ysaxon.github.io/boltworks/api/#boltworks.cli.argparse_decorator)

This allows you to use Python's argparse library to process complex command line flags and options in Slack Commands. A --help flag will be generated for you. And if your method is type hinted, you can use Automagic mode to create a parser automagically.

All Slack parameters will be passed through to your method; you can use the 'args' catchall, and/or individual arguments like 'respond' or 'context' etc
All other parameters will be parsed from the command string when the command is run.

#### The explicit way


```
# example taken from the argparser docs: https://docs.python.org/3/howto/argparse.html#conflicting-options

parser = argparse.ArgumentParser(description="calculate X to the power of Y")
group = parser.add_mutually_exclusive_group()
group.add_argument("-v", "--verbose", action="store_true")
group.add_argument("-q", "--quiet", action="store_true")
parser.add_argument("x", type=int, help="the base")
parser.add_argument("y", type=int, help="the exponent")
@app.command("/exponent")
@argparse_command(parser)
def power_calculator(respond,x,y,verbose,quiet):
    answer = x**y
    if quiet:
        respond(text=answer)
    elif verbose:
        respond(text=f"{x} to the power {y} equals {answer}")
    else:
        respond(text=f"{x}^{y} == {answer}")
                    
          
 ```
 
#### The automagic way

If you set automagic on, then providing an ArgParser is optional. Any type-hinted arguments not handled by an ArgParser you pass will be automagically added to an argparser with the appropriate names and types set. Lists, Optionals, Literals, default arguments, and primitive types all are supported.

```
from boltworks import argparse_command

@app.command(re.compile("/exponent"))
@argparse_command(automagic=True)
def perform_the_magic(respond, x: int, y:int, mode:Optional[Literal["q","v"]]=None):
    answer = x**y
    if mode=="q":
        respond(text=answer)
    elif mode=="v":
        respond(text=f"{x} to the power {y} equals {answer}")
    else:
        respond(text=f"{x}^{y} == {answer}")
```


## GUI - ActionCallbacks

[ActionCallbacks in docs](https://ysaxon.github.io/boltworks/api/#boltworks.cli.argparse_decorator)

This class allows you to easily serialize a method as a callback for a Slack UI element such as a button.
These callbacks can themselves post UI elements with more callbacks for more complicated logic, and you can always use the `partial` class to inject some arguments into the callback method at the time you are creating the callback, as in the below example.  

```
DISK_CACHE_DIR="~/.diskcache"
from boltworks import ActionCallbacks,DiskCacheKVSTore
from diskcache import Cache

disk_cache=DiskCacheKVStore(Cache(directory=DISK_CACHE_DIR))
callbacks=ActionCallbacks(app,disk_cache.using_serializer(dill))

def get_elapsed_time(args:Args, start:datetime):
    now = datetime.now()
    diff = now - start
    days, seconds = diff.days, diff.seconds
    hours, minutes, seconds = seconds // 3600, (seconds % 3600) // 60, seconds % 60

    formatted_diff = f"{days} day{'s' if days > 1 else ''}, "
    formatted_diff += f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    args.respond(f"time elapsed: {formatted_diff}")
    
def start_timer(args:Args):
  now=datetime.now()
  get_elapsed_button=callbacks.get_button_register_callback("get elapsed time",partial(get_elapsed_time,start=now))
  timer_started_message="Timer started at "+now.strftime("%A, %B %d, %Y %I:%M:%S %p")
  block=slack_sdk.models.blocks.SectionBlock(text=timer_started_message,accessory=get_elapsed_button)
  args.say(blocks=[block])


start_timer_button=callbacks.get_button_register_callback("start a timer",start_timer)
timer_start_block=slack_sdk.models.blocks.SectionBlock(text="click here to start a timer",accessory=start_timer_button)
app.client.chat_postMessage(blocks=[timer_start_block],channel=CHANNEL_ID)
```


## GUI - ThreadCallbacks

Similiar to ActionCallbacks, this class allows you to register a message's `ts` (timestamp used by slack as a message id), so that your callback will be called any time a message is posted to that Thread.

## GUI - NodeTreeUI

[TreeNodeUI class in docs](https://ysaxon.github.io/boltworks/api/#boltworks.gui.treenodeui.TreeNodeUI)

This module allows you to display complex nested information neatly, in a user-clickable, expanding and contracting view.
The TreeNodeUI class handles all the logic of formatting these trees and responding to clicks.

You just need to put your information into a tree datastructure, using the flexible TreeNode and ChildContainer classes.

### TreeNodes

Fundamentally a TreeNode has two things:

* A format it itself displays when it is visible, either a string, or for more complex formatting, a Slack Block or list of Blocks
* Children Nodes, organized into containers associated with UI elements that the user can click to hide or reveal that part of the tree.

### ChildContainers

There are two types of Child Containers.

* ButtonChildContainers, which each have a single list of Node Children; These are formatted as buttons and can be clicked to alternately expand/contract their children.
* MenuChildContainers, which each contain within them multiple labeled lists of Node Children. These can be formatted as static menus, overflow menus [...] or radio buttons, and in each case, selecting an option reveals its Node children.

Containers have a field for `child_pageination` which controls how many of its children are displayed at a time when they are visible; the rest will be accessed by clicking foward (and backward) buttons.

### The TreeNodeUI class

The TreeNodeUI class offers two methods for posting nodes (`post_single_node` and `post_treenodes`), and also handles all the logic of responding to UI callbacks and updating the tree.

### Instantiation

You can always directly instantiate a TreeNode or ChildContainer, but there are also static helper methods defined on some classes to help more easily construct frequently used variants of those classes. You can see some of them in action in the demos below. The most important of these are the ones which allow you to easily format an entire JSONlike object (ie what json.loads returns, a nested dict/list/primitive object) into a NodeTree.

**[See demos here in treenode.md](docs/treenode.md)**