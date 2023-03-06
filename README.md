# Boltworks

A collection of various extensions for Slack's bolt library to help you more easily make better slackbots.

## CLI - Argparse decorator

This allows you to use Python's argparse library to process complex command line flags and options in Slack Commands.

All Slack parameters will be passed through to your method; you can use the 'args' catchall, and/or individual arguments like 'respond' or 'context' etc
All other parameters will be parsed from the command string when the command is run.

#### The explicit way

```
from boltworks import argparse_command
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('main_input', help='the main input you want to give')
group = parser.add_mutually_exclusive_group()
group.add_argument('--verbose', action='store_true',
                   help='increase output verbosity')
group.add_argument('--quiet', action='store_true',
                   help='decrease output verbosity')
parser.add_argument('--algorithm', choices=['knn', 'svm', 'rf'],
                    help='choose the machine learning algorithm used')
parser.add_argument('--numbers', nargs='+', type=int,
                    help='list of numbers')
parser.add_argument('-f', '--flag', action='store_true',
                    help='toggle the flag')
                    
@app.command(re.compile("/dothething"))
@argparse_command(parser)
def do_the_thing(args: Args, main_input: str, verbose: bool, quiet: bool,
                 algorithm: Optional[str], numbers: Optional[List[int]], flag: bool):
    if numbers and not quiet:
        args.respond(f"your numbers sum to {sum(numbers)}")
    #etcetera
          
 ```
 
#### The automagic way

If you set automagic on, then providing an ArgParser is optional. Any type-hinted arguments not handled by an ArgParser you pass will be automagically added to an argparser with the appropriate names and types set. However there are some advanced features that aren't possible this way (such as mutually exclusive groups) and the help docs won't be as helpful.

```
from boltworks import argparse_command

@app.command(re.compile("/performthemagic"))
@argparse_command(automagic=True)
def perform_the_magic(args: Args, main_input: str, quiet:Optional[bool]=False, numbers: Optional[list[int]]=[]):
    if numbers and not quiet:
        args.respond(f"your numbers sum to {sum(numbers)}")
```


## GUI - ActionCallbacks

This class allows you to easily serialize a method as a callback for a Slack UI element such as a button.
These callbacks can themselves post UI elements with more callbacks for more complicated logic, and you can always use the `partial` class to inject some arguments into the callback method at the time you are creating the callback, as in the below example.  

```
DISK_CACHE_DIR="~/.diskcache"
from boltworks import ActionCallbacks,DiskCacheKVSTore
from diskcache import Cache #pip install diskcache

disk_cache=DiskCacheKVSTore(Cache(directory=DISK_CACHE_DIR))
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

This is the beefiest module of the repo. It allows you to display complex nested information neatly, in a user-clickable, expanding and contracting view.
The TreeNodeUI class handles all the logic of formatting these trees and responding to clicks.

You just need to put your information into the tree datastructure, using the flexible TreeNode and TreeNodeContainer classes.

Fundamentally a TreeNode has two things:

* A format it itself displays when it is visible, either a string, or for more complex formatting, a Slack Block or list thereof
* Children Nodes, organized into containers, that it can optionally hide or reveal.

The visibility of these Children Nodes is controlled by UI elements.
Fundamentally there are two types of Child Containers.

* regular ChildContainers, which have a single list of Node Children; These are formatted as buttons and can be clicked to expand/show their children, or clicked again to contract/hide their children.
* MenuChildContainers which contain within them multiple labeled lists of Node Children. These can be StaticMenus, OverflowMenus, or RadioButtons, and in each case, selecting an option reveals only its Children.

All the other fields you will see within TreeNodes and NodeContainers are concerned with the exact details of how those containers are formatted.

You can always directly instantiate a TreeNode or NodeContainer, but there are also static helper methods defined on some classes to help more easily construct frequently used variants of those classes.
Among these are methods to convert a jsonlike recursively nested dict/list object into a nested TreeNode.

(TODO: insert examples of TreeNode usage here)

```
