from __future__ import annotations
from common import TOKEN, APPTOKEN,DISK_CACHE_DIR,TEST_CHANNEL
from time import sleep
import diskcache
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.models.blocks import *
import sys
import os

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../..")
from boltworks import *

kvstore = DiskCacheKVStore(diskcache.core.Cache(DISK_CACHE_DIR))
app = App(token=TOKEN)
handler = SocketModeHandler(app, app_token=APPTOKEN)

handler.connect()
treenodeui = TreeNodeUI(app, kvstore)

months=TreeNode("There are a lot of months in the year",
                  [
                      ButtonChildContainer([
                          TreeNode("January"),
                          TreeNode("February"),
                          TreeNode("March"),
                          TreeNode("April"),
                          TreeNode("May"),
                          TreeNode("June"),
                          TreeNode("July"),
                          TreeNode("August"),
                          TreeNode("September"),
                          TreeNode("October"),
                          TreeNode("November"),
                          TreeNode("December"),
                      ], 
                        child_pageination=4)
                  ])

treenodeui.post_single_node(TEST_CHANNEL,months)
app.client.chat_postMessage(channel=TEST_CHANNEL,text=" \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n ")

seasons_buttons = TreeNode("These are the four seasons of a year",
                  children_containers=[ 
                   ButtonChildContainer([
                          TreeNode("December"),
                          TreeNode("January"),
                          TreeNode("February")], static_button_text="Winter"),
                   
                   ButtonChildContainer([
                          TreeNode("March"),
                          TreeNode("April"),
                          TreeNode("May")], static_button_text="Spring"),
                   
                   ButtonChildContainer([
                          TreeNode("June"),
                          TreeNode("July"),
                          TreeNode("August")], static_button_text="Summer"),
                   
                   ButtonChildContainer([
                          TreeNode("September"),
                          TreeNode("October"),
                          TreeNode("November")], static_button_text="Fall"),
                  ])
treenodeui.post_single_node(TEST_CHANNEL,seasons_buttons)
app.client.chat_postMessage(channel=TEST_CHANNEL,text=" \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n ")

seasons_menu = TreeNode("Which season would you like to know more about?",
                  children_containers=StaticSelectMenuChildContainer([
                      MenuOption("Winter", [
                          TreeNode("December"),
                          TreeNode("January"),
                          TreeNode("February")
                      ]),
                      MenuOption("Spring", [
                          TreeNode("March"),
                          TreeNode("April"),
                          TreeNode("May")
                      ]),
                      MenuOption("Summer", [
                          TreeNode("June"),
                          TreeNode("July"),
                          TreeNode("August")
                      ]),
                      MenuOption("Fall", [
                          TreeNode("September"),
                          TreeNode("October"),
                          TreeNode("November")
                      ])
                  ]))

treenodeui.post_single_node(TEST_CHANNEL,seasons_menu)
app.client.chat_postMessage(channel=TEST_CHANNEL,text=" \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n ")


seasons_json={
  "Winter": [
    {"month": "December"},
    {"month": "January"},
    {"month": "February"}
  ],
  "Spring": [
    {"month": "March"},
    {"month": "April"},
    {"month": "May"}
  ],
  "Summer": [
    {"month": "June"},
    {"month": "July"},
    {"month": "August"}
  ],
  "Fall": [
    {"month": "September"},
    {"month": "October"},
    {"month": "November"}
  ]
}

seasons_json_node=TreeNode("There are a bunch of seasons and each one has three months",
         ButtonChildContainer.forJsonDetails(seasons_json))

treenodeui.post_single_node(TEST_CHANNEL,seasons_json_node)
app.client.chat_postMessage(channel=TEST_CHANNEL,text=" \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n ")



seasons_nodes = [
    TreeNode.withSimpleSideButton("Winter", [
        TreeNode("December"),
        TreeNode("January"),
        TreeNode("February")
    ]),
    TreeNode.withSimpleSideButton("Spring", [
        TreeNode("March"),
        TreeNode("April"),
        TreeNode("May")
    ]),
    TreeNode.withSimpleSideButton("Summer", [
        TreeNode("June"),
        TreeNode("July"),
        TreeNode("August")
    ]),
    TreeNode.withSimpleSideButton("Fall", [
        TreeNode("September"),
        TreeNode("October"),
        TreeNode("November")
    ])
]

treenodeui.post_treenodes(TEST_CHANNEL,seasons_nodes,global_header="These are the four seasons",post_all_together=False)
app.client.chat_postMessage(channel=TEST_CHANNEL,text=" \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n ")



hotel_node=TreeNode.withSimpleSideButton(
    "We found *6 Hotels* in New Orleans, LA from *12/14 to 12/17*",
    child_pageination=3,
    children=[
        
TreeNode([
    SectionBlock(
        text="*<fakeLink.toHotelPage.com|Windsor Court Hotel>*\n★★★★★\n$340 per night\nRated: 9.4 - Excellent",
        accessory=ImageElement(
            image_url="https://api.slack.com/img/blocks/bkb_template_images/tripAgent_1.png",
            alt_text="Windsor Court Hotel thumbnail"
        )
    ),
    ContextBlock(elements=[
        ImageElement(image_url="https://api.slack.com/img/blocks/bkb_template_images/tripAgentLocationMarker.png",
                     alt_text="Location Pin Icon"),
        TextObject(type="plain_text",text="Location: Central Business District"),
        
    ]),
    DividerBlock()
]),

TreeNode([SectionBlock(
        text="*<fakeLink.toHotelPage.com|The Ritz-Carlton New Orleans>*\n★★★★★\n$340 per night\nRated: 9.1 - Excellent",
        accessory=ImageElement(
            image_url="https://api.slack.com/img/blocks/bkb_template_images/tripAgent_2.png",
            alt_text="Ritz-Carlton New Orleans thumbnail"
        )
    ),
    ContextBlock(elements=[
        ImageElement(image_url="https://api.slack.com/img/blocks/bkb_template_images/tripAgentLocationMarker.png",
                     alt_text="Location Pin Icon"),
        TextObject(type="plain_text",text="Location: French Quarter"),
        
    ]),
    DividerBlock()
]),


TreeNode(
    [SectionBlock(
        text="*<fakeLink.toHotelPage.com|Omni Royal Orleans Hotel>*\n★★★★★\n$419 per night\nRated: 8.8 - Excellent",
        accessory=ImageElement(
            image_url="https://api.slack.com/img/blocks/bkb_template_images/tripAgent_3.png",
            alt_text="Omni Royal Orleans Hotel thumbnail"
        )
    ),
    ContextBlock(elements=[
        ImageElement(image_url="https://api.slack.com/img/blocks/bkb_template_images/tripAgentLocationMarker.png",
                     alt_text="Location Pin Icon"),
        TextObject(type="plain_text",text="Location: French Quarter"),
        
    ]),
    DividerBlock()]
),

TreeNode([SectionBlock(
        text="*<fakeLink.toHotelPage.com|The Roosevelt New Orleans, A Waldorf Astoria Hotel>*\n★★★★★\n$299 per night\nRated: 9.3 - Excellent",
        accessory=ImageElement(
            image_url="https://upload.wikimedia.org/wikipedia/en/2/2c/Ambassador_Hotel_Kaohsiung_at_Night.jpeg",
            alt_text="The Roosevelt New Orleans, A Waldorf Astoria Hotel thumbnail"
        )
    ),
    ContextBlock(elements=[
        ImageElement(image_url="https://api.slack.com/img/blocks/bkb_template_images/tripAgentLocationMarker.png",
                     alt_text="Location Pin Icon"),
        TextObject(type="plain_text",text="Location: Central Business District"),
        
    ]),
    DividerBlock(),
    ]),

TreeNode([
   SectionBlock(
        text="*<fakeLink.toHotelPage.com|The Pontchartrain Hotel>*\n★★★★\n$229 per night\nRated: 8.9 - Excellent",
        accessory=ImageElement(
            image_url="https://live.staticflickr.com/65535/50033621878_24a67c0281_b.jpg",
            alt_text="The Pontchartrain Hotel thumbnail"
        )
    ),
    ContextBlock(elements=[
        ImageElement(image_url="https://api.slack.com/img/blocks/bkb_template_images/tripAgentLocationMarker.png",
                     alt_text="Location Pin Icon"),
        TextObject(type="plain_text",text="Location: Garden District"),
        
    ]),
    DividerBlock(),
    ]),

TreeNode([
    SectionBlock(
        text="*<fakeLink.toHotelPage.com|Ace Hotel New Orleans>*\n★★★★\n$239 per night\nRated: 8.7 - Excellent",
        accessory=ImageElement(
            image_url="https://ygt-res.cloudinary.com/image/upload/c_fit,h_1280,q_80,w_1920/v1656076242/Venues/Hotel%20Las%20Palmeras/Las_Palmeras_Affiliated_Hotel_Pool.3428_gipozg.jpg",
            alt_text="Ace Hotel New Orleans thumbnail"
        )
    ),
    ContextBlock(elements=[
        ImageElement(image_url="https://api.slack.com/img/blocks/bkb_template_images/tripAgentLocationMarker.png",
                     alt_text="Location Pin Icon"),
        TextObject(type="plain_text",text="Location: Warehouse District"),
        
    ]),
    DividerBlock(),
    ]),
])

treenodeui.post_single_node(TEST_CHANNEL,hotel_node,expand_first=True)
app.client.chat_postMessage(channel=TEST_CHANNEL,text=" \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n ")

while True:
    sleep(1)