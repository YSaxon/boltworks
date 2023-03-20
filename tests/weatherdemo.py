from __future__ import annotations
from datetime import datetime, timedelta
from functools import partial
from time import sleep
from typing import Literal
from diskcache import Cache
import diskcache
import pytest
from slack_bolt import App, Args
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.models.blocks import SectionBlock
import slack_sdk.models.blocks
import dill

from slack_sdk.models import blocks

from boltworks import *

import sys
import os
from boltworks.gui.treenodeui import TreeNode

from common import DISK_CACHE_DIR

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../..")

from boltworks import ActionCallbacks
from boltworks import DiskCacheKVStore

from common import TOKEN,APPTOKEN
import sys
import os
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../..")
from boltworks import ActionCallbacks, DiskCacheKVStore

kvstore = DiskCacheKVStore(diskcache.core.Cache(DISK_CACHE_DIR)).using_serializer(dill)
app = App(token=TOKEN)
handler = SocketModeHandler(app, app_token=APPTOKEN)
callbacks = ActionCallbacks(app, kvstore)


from common import TEST_CHANNEL


#  {
#                 "date": "2023-03-20",
#                 "date_epoch": 1679270400,
#                 "day": {
#                     "maxtemp_c": 11.6,
#                     "maxtemp_f": 52.9,
#                     "mintemp_c": -2.9,
#                     "mintemp_f": 26.8,
#                     "avgtemp_c": 3.1,
#                     "avgtemp_f": 37.6,
#                     "maxwind_mph": 9.6,
#                     "maxwind_kph": 15.5,
#                     "totalprecip_mm": 0.0,
#                     "totalprecip_in": 0.0,
#                     "totalsnow_cm": 0.0,
#                     "avgvis_km": 10.0,
#                     "avgvis_miles": 6.0,
#                     "avghumidity": 54.0,
#                     "daily_will_it_rain": 0,
#                     "daily_chance_of_rain": 0,
#                     "daily_will_it_snow": 0,
#                     "daily_chance_of_snow": 0,
#                     "condition": {
#                         "text": "Sunny",
#                         "icon": "//cdn.weatherapi.com/weather/64x64/day/113.png",
#                         "code": 1000
#                     },
#                     "uv": 2.0,
#                     "air_quality": {
#                         "co": 256.8920007324219,
#                         "no2": 4.7399999713897705,
#                         "o3": 92.95599945068359,
#                         "so2": 1.2639999985694885,
#                         "pm2_5": 1.8999999785423278,
#                         "pm10": 2.327999994754791,
#                         "us-epa-index": 1,
#                         "gb-defra-index": 1
#                     }
#                 },
def format_day(weather_dict,units:Literal["imperial","metric"])->slack_sdk.models.blocks.Block:
    day_of_week=get_day_of_week(weather_dict['date'])
    simple_format=SectionBlock(
        text=f"{weather_dict['day']['condition']['text']} {weather_dict['day']['maxtemp_f'] if units=='imperial' else weather_dict['day']['maxtemp_c']} / {weather_dict['day']['mintemp_f'] if units=='imperial' else weather_dict['day']['mintemp_c']}",
        accessory=blocks.ImageElement(image_url='http:'+weather_dict['day']['condition']['icon'])
        )
    return simple_format

def get_day_of_week(date:str)->str:
    return datetime.strptime(date,"%Y-%m-%d").strftime("%A")

def get_tree_node_day(weather_dict,units:Literal["imperial","metric"]):
    node=TreeNode(format_day(weather_dict,units),
                  children_containers=[
                     ButtonChildContainer.forJsonDetails(weather_dict['day']['air_quality'],'AirQuality')
                     ButtonChildContainer.forJsonDetails(weather_dict['day']['air_quality'],'Temp')
                  ])


handler.connect()
while True:
    sleep(1)