from __future__ import annotations
from datetime import datetime
import json
from time import sleep
from typing import Literal
import diskcache
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.models.blocks import SectionBlock
import slack_sdk.models.blocks
import sys
import os

from slack_sdk.models import blocks
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../..")

from boltworks import *

from boltworks import TreeNode

from common import DISK_CACHE_DIR


from boltworks import ActionCallbacks
from boltworks import DiskCacheKVStore

from common import TOKEN,APPTOKEN
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../..")
from boltworks import ActionCallbacks, DiskCacheKVStore

kvstore = DiskCacheKVStore(diskcache.core.Cache(DISK_CACHE_DIR))
app = App(token=TOKEN)
handler = SocketModeHandler(app, app_token=APPTOKEN)
callbacks = ActionCallbacks(app, kvstore)




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
    simple_format=SectionBlock(
        text=f"*{get_day_of_week(weather_dict['date'])}*: {weather_dict['day']['condition']['text']}\nHi {weather_dict['day']['maxtemp_f'] if units=='imperial' else weather_dict['day']['maxtemp_c']}° / Lo {weather_dict['day']['mintemp_f'] if units=='imperial' else weather_dict['day']['mintemp_c']}°",
        accessory=blocks.ImageElement(image_url='http:'+weather_dict['day']['condition']['icon'],alt_text=weather_dict["day"]['condition']["text"])
        )
    return simple_format

# {
#                         "time_epoch": 1679457600,
#                         "time": "2023-03-22 00:00",
#                         "temp_c": 1.9,
#                         "temp_f": 35.4,
#                         "is_day": 0,
#                         "condition": {
#                             "text": "Partly cloudy",
#                             "icon": "//cdn.weatherapi.com/weather/64x64/night/116.png",
#                             "code": 1003
#                         },
#                         "wind_mph": 1.8,
#                         "wind_kph": 2.9,
#                         "wind_degree": 9,
#                         "wind_dir": "N",
#                         "pressure_mb": 1029.0,
#                         "pressure_in": 30.39,
#                         "precip_mm": 0.0,
#                         "precip_in": 0.0,
#                         "humidity": 88,
#                         "cloud": 44,
#                         "feelslike_c": 1.9,
#                         "feelslike_f": 35.4,
#                         "windchill_c": 1.9,
#                         "windchill_f": 35.4,
#                         "heatindex_c": 1.9,
#                         "heatindex_f": 35.4,
#                         "dewpoint_c": 0.2,
#                         "dewpoint_f": 32.4,
#                         "will_it_rain": 0,
#                         "chance_of_rain": 0,
#                         "will_it_snow": 0,
#                         "chance_of_snow": 0,
#                         "vis_km": 10.0,
#                         "vis_miles": 6.0,
#                         "gust_mph": 3.8,
#                         "gust_kph": 6.1,
#                         "uv": 1.0,
#                         "air_quality": {
#                             "co": 440.6000061035156,
#                             "no2": 37.70000076293945,
#                             "o3": 22.399999618530273,
#                             "so2": 0.30000001192092896,
#                             "pm2_5": 15.0,
#                             "pm10": 18.100000381469727,
#                             "us-epa-index": 1,
#                             "gb-defra-index": 2
#                         }
#                     },
def format_hour(weather_dict,units:Literal["imperial","metric"])->slack_sdk.models.blocks.Block:
    simple_format=SectionBlock(
        text=f"*{get_hour_of_day(weather_dict['time'])}*: {weather_dict['condition']['text']} {weather_dict['temp_f'] if units=='imperial' else weather_dict['temp_c']}°, feels like {weather_dict['feelslike_f'] if units=='imperial' else weather_dict['feelslike_c']}°, %{weather_dict['chance_of_rain']} chance rain",
        accessory=blocks.ImageElement(image_url='http:'+weather_dict['condition']['icon'],alt_text=weather_dict['condition']["text"])
        )
    return simple_format

def get_day_of_week(date:str)->str:
    return datetime.strptime(date,"%Y-%m-%d").strftime("%A")
def get_hour_of_day(date:str)->str:
    return datetime.strptime(date,"%Y-%m-%d %H:%M").strftime("%-I%p")

def get_tree_node_day(weather_dict,units:Literal["imperial","metric"]):
    return TreeNode(format_day(weather_dict,units),
                  children_containers=[
                     ButtonChildContainer.forJsonDetails(weather_dict['day']['air_quality'],'AirQuality'),
                     ButtonChildContainer.forJsonDetails(weather_dict['astro'],'Astronomic'),
                     ButtonChildContainer(child_nodes=[
                         TreeNode.fromJson(format_hour(h,units),h) for h in weather_dict['hour']
                         ],static_button_text='Hourly',child_pageination=6),
                  ])

def format_root_weather(weather_dict):
    return SectionBlock(text=f"Weather for {weather_dict['location']['name']}, retrieved {weather_dict['location']['localtime']}")

def unit_weather_results(weather_dict,units:Literal["imperial","metric"]):
    return TreeNode(" ",
                   [
                       ButtonChildContainer(child_nodes=[
                         get_tree_node_day(d,units) for d in weather_dict['forecast']['forecastday']
                         ],static_button_text='Forecast',child_pageination=6),
                       ButtonChildContainer.forJsonDetails(weather_dict['location'],'Location'),
                       ButtonChildContainer.forJsonDetails(weather_dict['alerts'],'Alerts'),
                   ] )

def get_root_weather_results_nodes(weather_dict,units:Literal["imperial","metric","not_specified"]="not_specified"):
    if units=="not_specified":
        nodes=[
            TreeNode(format_root_weather(weather_dict),
                StaticSelectMenuChildContainer(
                    [
                        MenuOption("Imperial",unit_weather_results(weather_dict,"imperial")),
                        MenuOption("Metric",unit_weather_results(weather_dict,"metric")),]
                ))]
    else:
        nodes=[TreeNode(format_root_weather(weather_dict)),
               unit_weather_results(weather_dict,units)]
    return nodes
        
        
        
    
    


handler.connect()
with open("/Users/ysaxon/Desktop/slackbot/python/boltworks/tests/weather_demo_data.json",'r') as f:
    weather_data= json.loads(f.read())
treenodeui=TreeNodeUI(app,kvstore)
treenodeui.post_treenodes("C04UQ8N7RU5",get_root_weather_results_nodes(weather_data),False)

while True:
    sleep(1)