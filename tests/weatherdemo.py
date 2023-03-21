from __future__ import annotations
import requests
import dill
from functools import partial
from common import TOKEN, APPTOKEN, WEATHER_API_KEY
from common import DISK_CACHE_DIR
from datetime import datetime
import json
from time import sleep
from typing import Literal,Optional
import diskcache
from slack_bolt import App, Args
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.models.blocks import SectionBlock
import slack_sdk.models.blocks
import sys
import os

from slack_sdk.models import blocks
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../..")
from boltworks import *

kvstore = DiskCacheKVStore(diskcache.core.Cache(DISK_CACHE_DIR))
app = App(token=TOKEN)
handler = SocketModeHandler(app, app_token=APPTOKEN)
callbacks = ActionCallbacks(app, kvstore.using_serializer(dill))


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
def format_day(weather_dict, units: Literal["imperial", "metric"]) -> slack_sdk.models.blocks.Block:
    day_of_week = datetime.strptime(weather_dict['date'], "%Y-%m-%d").strftime("%A")
    simple_format = SectionBlock(
        text=f"*{day_of_week}*: {weather_dict['day']['condition']['text']}\nHi {weather_dict['day']['maxtemp_f'] if units=='imperial' else weather_dict['day']['maxtemp_c']}° / Lo {weather_dict['day']['mintemp_f'] if units=='imperial' else weather_dict['day']['mintemp_c']}°\n"
        f"Precipitation: %{max(weather_dict['day']['daily_chance_of_rain'],weather_dict['day']['daily_chance_of_snow'])}\n"
        f"Avg Humidity: %{weather_dict['day']['avghumidity']}\n"
        f"Max Wind: {(str(weather_dict['day']['maxwind_mph'])+' mph') if units=='imperial' else (str(weather_dict['day']['maxwind_kph'])+' kph')}",
        accessory=blocks.ImageElement(
            image_url='http:' + weather_dict['day']['condition']['icon'], alt_text=weather_dict["day"]['condition']["text"])
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


def format_hour(weather_dict, units: Literal["imperial", "metric"]) -> slack_sdk.models.blocks.Block:
    hour_of_day = datetime.strptime(
        weather_dict['time'], "%Y-%m-%d %H:%M").strftime("%-I%p")
    simple_format = SectionBlock(
        text=f"*{hour_of_day}*: {weather_dict['condition']['text']} | {weather_dict['temp_f'] if units=='imperial' else weather_dict['temp_c']}° | feels {weather_dict['feelslike_f'] if units=='imperial' else weather_dict['feelslike_c']}° | %{weather_dict['chance_of_rain']} rain | Wind {(str(weather_dict['wind_mph'])+' mph') if units=='imperial' else (str(weather_dict['wind_kph'])+' kph')} {weather_dict['wind_dir']}",
        accessory=blocks.ImageElement(
            image_url='http:' + weather_dict['condition']['icon'], alt_text=weather_dict['condition']["text"])
    )
    return simple_format


def get_days_weather_node(weather_dict, units: Literal["imperial", "metric"]):
    containers = [
        ButtonChildContainer(child_nodes=
                             [TreeNode.fromJson(format_hour(h, units), h) for h in weather_dict['hour']],
                             static_button_text='Hourly Forecast', child_pageination=6),
        ButtonChildContainer.forJsonDetails(weather_dict['astro'], 'Astronomic Data'),
    ]
    if 'air_quality' in weather_dict['day']:
        containers.append(
            ButtonChildContainer.forJsonDetails(weather_dict['day']['air_quality'], 'Air Quality')
        )
    return TreeNode(format_day(weather_dict, units),
                    children_containers=containers)


def get_root_weather_results_node(weather_dict, units: Literal["imperial", "metric", "not_specified"] = "not_specified"):
    forecast: StaticSelectMenuChildContainer | ButtonChildContainer
    if units == "not_specified":
        forecast = StaticSelectMenuChildContainer(
            [MenuOption(u.capitalize(), [get_days_weather_node(
                d, u) for d in weather_dict['forecast']['forecastday']]) for u in ("imperial", "metric")],
            placeholder="Forecast units", child_pageination=4
        )
    else:
        forecast = ButtonChildContainer(child_nodes=[
            get_days_weather_node(d, units) for d in weather_dict['forecast']['forecastday']
        ], static_button_text='Forecast', child_pageination=4)
    node = TreeNode(
        SectionBlock(
            text=f"Weather for {weather_dict['location']['name']}, retrieved {weather_dict['location']['localtime']}"),
        children_containers=[
            forecast,
            ButtonChildContainer.forJsonDetails(
                weather_dict['location'], 'Location Data'),
        ],
    )
    if 'alerts' in weather_dict and 'alert' in weather_dict['alerts']:
        node.children_containers.append(ButtonChildContainer(
            [TreeNode(
                f"[{i+1}]: {a['event']}" + (f" for {a['areas']}" if a['areas'] else ""),
                ButtonChildContainer.forJsonDetails(a)) for i, a in enumerate(weather_dict['alerts']['alert'])], 'Special Weather Alerts'))
    return node


handler.connect()
with open("/Users/ysaxon/Desktop/slackbot/python/boltworks/tests/weather_demo_data.json", 'r') as f:
    weather_data = json.loads(f.read())
treenodeui = TreeNodeUI(app, kvstore)
treenodeui.post_single_node("C04UQ8N7RU5", get_root_weather_results_node(weather_data))


@app.command("/weather")
@argparse_command(automagic=True)
def get_and_post_weather(args: Args, location: str, days: int = 3, *, aqi=True, alerts=True, units:list[Literal["metric","imperial"]]=["metric","imperial"]):
    u = units[0] if len(units)==1 else "not_specified"
    response = requests.get("http://api.weatherapi.com/v1/forecast.json", params=dict(key=WEATHER_API_KEY,
                            q=location, days=days, aqi="yes" if aqi else "no", alerts="yes" if alerts else "no"))
    weather = response.json()
    node = get_root_weather_results_node(weather,u)
    treenodeui.post_single_node(args.say, node)


while True:
    sleep(1)
