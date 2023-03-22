# TreeNodeUI

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

## Simple examples

### Months of the year, pageinated

Here's the simplest possible demo to get us started

```
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
```

We're using a single ButtonChildContainer, which defaults to being on the side of the original node, and applying a pageination of 4 to the months, so they display 4 at a time.

#### Seasons as buttons in a row, with months as children

```
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
```

#### Seasons as a StaticSelectMenu

```
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
```

#### Using a JSON adapter helper methods

```
seasons_jsonlike={
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
```

### Posting multiple nodes together (and using withSimpleSideButton)

```
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
```

#### Fancy Slack block formatting
All the examples until now have used simple strings for the formatting blocks, but you can be as fancy as you like, and use any Blocks that Slack provides

```
from slack_sdk.models.blocks import *

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
```

## Putting it all together: the Weather Forecast Example

Lets build a CLI command for requesting a weather forecast and displaying it as a NodeTree. 

First the CLI method. We'll use `api.weatherapi.com` for obtaining the forecast and build a CLI method around it, and create the parser automagically.

```
@app.command("/weather")
@argparse_command(automagic=True)
def get_and_post_weather(args: Args, location: str, days: int = 3, *, aqi=True, alerts=True, units:list[Literal["metric","imperial"]]=["metric","imperial"]):
    u = units[0] if len(units)==1 else "not_specified"
    response = requests.get("http://api.weatherapi.com/v1/forecast.json", params=dict(key=WEATHER_API_KEY,
                            q=location, days=days, aqi="yes" if aqi else "no", alerts="yes" if alerts else "no"))
    weather = response.json()
    node = get_root_weather_results_node(weather,u)
    treenodeui.post_single_node(args.say, node)
```


It's usually easiest to start at the bottom level (the leaf nodes) and work your way backwards to the root from there. So let's start by formatting a node to show an hourly forecast.

The following two functions will return a Slack Blocks representing an hourly and daily forecast respectively
```
def format_hour(weather_dict, units: Literal["imperial", "metric"]) -> slack_sdk.models.blocks.Block:
    hour_of_day = datetime.strptime(
        weather_dict['time'], "%Y-%m-%d %H:%M").strftime("%-I%p")
    simple_format = SectionBlock(
        text=f"*{hour_of_day}*: {weather_dict['condition']['text']} | {weather_dict['temp_f'] if units=='imperial' else weather_dict['temp_c']}° | feels {weather_dict['feelslike_f'] if units=='imperial' else weather_dict['feelslike_c']}° | {weather_dict['chance_of_rain']}% rain | Wind {(str(weather_dict['wind_mph'])+' mph') if units=='imperial' else (str(weather_dict['wind_kph'])+' kph')} {weather_dict['wind_dir']}",
        accessory=blocks.ImageElement(
            image_url='http:' + weather_dict['condition']['icon'], alt_text=weather_dict['condition']["text"])
    )
    return simple_format
```

```
def format_day(weather_dict, units: Literal["imperial", "metric"]) -> slack_sdk.models.blocks.Block:
    day_of_week = datetime.strptime(weather_dict['date'], "%Y-%m-%d").strftime("%A")
    simple_format = SectionBlock(
        text=f"*{day_of_week}*: {weather_dict['day']['condition']['text']}\nHi {weather_dict['day']['maxtemp_f'] if units=='imperial' else weather_dict['day']['maxtemp_c']}° / Lo {weather_dict['day']['mintemp_f'] if units=='imperial' else weather_dict['day']['mintemp_c']}°\n"
        f"Precipitation: {max(weather_dict['day']['daily_chance_of_rain'],weather_dict['day']['daily_chance_of_snow'])}%\n"
        f"Avg Humidity: {weather_dict['day']['avghumidity']}%\n"
        f"Max Wind: {(str(weather_dict['day']['maxwind_mph'])+' mph') if units=='imperial' else (str(weather_dict['day']['maxwind_kph'])+' kph')}",
        accessory=blocks.ImageElement(
            image_url='http:' + weather_dict['day']['condition']['icon'], alt_text=weather_dict["day"]['condition']["text"])
    )
    return simple_format
```

Now we make a method to create a node for the daily and hourly forecasts:
```
def get_days_weather_node(weather_dict, units: Literal["imperial", "metric"]) -> TreeNode:
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
```
So what we just did was define the child containers for the daily_forecast nodes. We set the hourly forecast button container to contain Nodes for every hour with the format from the method we defined before, and containing a detail button on their side for displaying the full Json of that hourly forecast. We are similiarly using a ButtonChildContainer.forJsonDetails for the daily air quality (if that exists in the forecast), and for the daily astronomical data.

Now let's put it together into a RootNode.

```
def get_root_weather_results_node(weather_dict, units: Literal["imperial", "metric", "not_specified"] = "not_specified"):
    forecast: StaticSelectMenuChildContainer | ButtonChildContainer
    if units == "not_specified":
        forecast = StaticSelectMenuChildContainer(
            [MenuOption(u.capitalize(), 
            [get_days_weather_node(d, u) for d in weather_dict['forecast']['forecastday']]) for u in ("imperial", "metric")],
            placeholder="Forecast units", child_pageination=4)
    else:
        forecast = ButtonChildContainer(child_nodes=[
            get_days_weather_node(d, units) for d in weather_dict['forecast']['forecastday']],
            static_button_text='Forecast', child_pageination=4)
            
    node = TreeNode(SectionBlock(
            text=f"Weather for {weather_dict['location']['name']}, as of {weather_dict['location']['localtime']}"),
            children_containers=[
                forecast, #the button or menu we defined above
                ButtonChildContainer.forJsonDetails(
                    weather_dict['location'], 'Location Data')])
                    
    if 'alerts' in weather_dict and 'alert' in weather_dict['alerts']:
        node.children_containers.append(ButtonChildContainer(
            [TreeNode(
                f"[{i+1}]: {a['event']}" + (f" for {a['areas']}" if a['areas'] else ""),
                ButtonChildContainer.forJsonDetails(a)) for i, a in enumerate(weather_dict['alerts']['alert'])], 'Special Weather Alerts'))
    return node
```

We're doing the same sort of thing here again. If we already know the user's units preference, we are the daily forecast into a button. Otherwise we will put a tree representing each unit type into a menu. Then we are putting that, and a JsonDetails button for location data, and another custom defined ButtonChildContainer for each special weather alert if those exist, into the new Node which we are returning.


And just like that we have a super nice dynamically formatted weather forecast view!
