from __future__ import annotations
from common import TOKEN, APPTOKEN, DISK_CACHE_DIR
from common import TEST_CHANNEL
from datetime import datetime, timedelta
from functools import partial
from time import sleep
import diskcache
from slack_bolt import App, Args
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.models.blocks import SectionBlock, ActionsBlock
import dill


import sys
import os
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../..")
from boltworks import ActionCallbacks, DiskCacheKVStore



kvstore = DiskCacheKVStore(diskcache.core.Cache(DISK_CACHE_DIR)).using_serializer(dill)
app = App(token=TOKEN)
handler = SocketModeHandler(app, app_token=APPTOKEN)
callbacks = ActionCallbacks(app, kvstore)


def format_timedelta(diff: timedelta):
    days, seconds = diff.days, diff.seconds
    hours, minutes, seconds = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    milliseconds = int((diff.microseconds % 1e6) // 1e5)

    formatted_diff = ""
    if days:
        formatted_diff += f"{days} day{'s' if days > 1 else ''}, "
    if days or hours:
        formatted_diff += f"{hours:02d}:"
    formatted_diff += f"{minutes:02d}:{seconds:02d}.{milliseconds:01d}"
    return formatted_diff


def get_elapsed_time(args: Args, start: datetime):
    args.ack()
    now = datetime.now()
    diff = now - start
    formatted_diff = format_timedelta(diff)
    args.respond(f"Time elapsed: {formatted_diff}", replace_original=False)


def start_timer(args: Args):
    args.ack()
    now = datetime.now()
    get_elapsed_button = callbacks.get_button_register_callback(
        "get elapsed time", partial(get_elapsed_time, start=now))
    timer_started_message = "Timer started at " + \
        now.strftime("%A, %B %d, %Y %I:%M:%S %p")
    blocks = SectionBlock(text=timer_started_message, accessory=get_elapsed_button)
    args.say(blocks=[blocks])




# more complex version below


def running(previously_elapsed: timedelta, started_time: datetime, laps: list[timedelta] = []):
    def lap_action(args: Args):
        now_elapsed = previously_elapsed + (datetime.now() - started_time)
        args.respond(replace_original=True, blocks=running(previously_elapsed, started_time, laps + [now_elapsed]))

    def update_action(args: Args):
        args.respond(replace_original=True, blocks=running(previously_elapsed, started_time, laps))

    def stop_action(args: Args):
        now_elapsed = previously_elapsed + (datetime.now() - started_time)
        args.respond(replace_original=True, blocks=stopped(now_elapsed, laps))
        
    now_elapsed = previously_elapsed + (datetime.now() - started_time)
    blocks = [
        SectionBlock(text=format_timedelta(now_elapsed),accessory=callbacks.get_button_register_callback("update", update_action)),
        ActionsBlock(elements=[
            callbacks.get_button_register_callback("lap", lap_action),
            callbacks.get_button_register_callback("stop", stop_action)])]
    
    if laps:
        blocks.append(SectionBlock(text="\n".join(
            [format_timedelta(d)for d in laps])))
        
    return blocks


def stopped(previously_elapsed: timedelta, laps: list[timedelta] = []):
    def reset_action(args: Args):
        args.respond(replace_original=True, blocks=stopped(timedelta(), []))

    def start_action(args: Args):
        args.respond(replace_original=True, blocks=running(
            previously_elapsed, datetime.now(), laps))
        
    buttons=[
        callbacks.get_button_register_callback("start", start_action)]
    if previously_elapsed:
        buttons.append(callbacks.get_button_register_callback("reset", reset_action))
        
    blocks = [
        SectionBlock(text=format_timedelta(previously_elapsed)),
        ActionsBlock(elements=buttons)]
    
    if laps:
        blocks.append(SectionBlock(text="\n".join(
            [format_timedelta(d)for d in laps])))
        
    return blocks



# start_timer_button=callbacks.get_button_register_callback("start a timer",start_timer)
# timer_start_blocks=SectionBlock(text="Click here to start a timer",accessory=start_timer_button)
# app.client.chat_postMessage(blocks=[timer_start_blocks],channel=TEST_CHANNEL)
handler.connect()


app.client.chat_postMessage(blocks=stopped(timedelta(), []), channel="C04UQ8N7RU5")

while True:
    sleep(1)
