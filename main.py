from flask import Flask
from flask import request
from pymessenger.bot import Bot
from credentials import credentials,db_creds
from pymongo import MongoClient
import get_food_data  # yelp
import botutils
import random


# import credential keys
ACCESS_TOKEN = credentials['ACCESS_TOKEN']
VERIFY_TOKEN = credentials['VERIFY_TOKEN']

# init db
db_username = db_creds['user_name']
db_password = db_creds['password']
db_appname  = db_creds['app_name']
client = MongoClient('mongodb://{0}:{1}@ds141464.mlab.com:41464/{2}'.format(db_username,db_password,db_appname))
db = client[db_appname]
# db collection
users = db.senorbottousers

location = "none"

def get_user_from_db(db_userId,searchKey):
    """ Looks for the specified user in the db and then queries
        the searchKey in it. SearchKey should match any of the doc
        inside a collection. Use to get the current value in any doc.
    """
    key = None
    __user_cursor = users.find({"user_id":db_userId}).limit(1)
    for _u in __user_cursor:
        key = _u[searchKey]
    return key

def db_update_document(db_userId,update_list):
    """ Updates a specified doc containing the matched userId with some info.
        Second arg is a list having 2 value ['key','value']
    """
    users.update({'user_id':db_userId},{'$set':{'{}'.format(update_list[0]):update_list[1]}})

def db_update_and_increment(db_userId,dockey):
    """ Updates the current docKey value by +1"""
    users.update_one({'user_id':db_userId},{'$inc':{'{}'.format(dockey):1}},upsert=True)

#___________________________________________________________________________________________



#____________________________________________________________________________________________


app = Flask(__name__)
# set up messenger wrapper
bot = Bot(ACCESS_TOKEN)


x = botutils.GetStartedButton_createBtn()
botutils.Persistant_menu()

@app.route('/')
def index():
    return 'ok'
# verify fb's request with the token
# this is a one-time verification, so every time you open the page it'll show an error
# the best thing to cover it is to place a nice looking page.
@app.route('/testbot',methods=['GET'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        else:
            # let the invalid verify pass silently
            pass


# recieve messages and pass it to some function which parses it further
@app.route('/testbot',methods=['POST'])
def recieve_incoming_messages():
    # just chilling babe!
    global location
    location = "none"
    if request.method == "POST":
        output = request.get_json()
        # for normal text messages
        # get the recipient id and user message from the JSON response
        user_payload = "@none"
        recipient_id = "@none"
        user_message = ""

        for event in output['entry']:
            if event.get('messaging'):
                messaging = event['messaging']
                for x in messaging:
                    if x.get('message'):
                        recipient_id = x['sender']['id']
                        if x['message'].get('text'):
                            user_message = x['message']['text']
                        if x['message'].get('quick_reply'):
                            user_payload = x['message']['quick_reply']['payload']
                        if x['message'].get('attachments'):
                            if x['message']['attachments'][0].get('payload'):
                                if x['message']['attachments'][0]['payload'].get('coordinates'):
                                    location = x['message']['attachments'][0]['payload']['coordinates']
                                    # db_update_document(recipient_id,["location",location])
                    if x.get('postback'):  # for postback getstarted button
                        recipient_id = x['sender']['id']
                        if x['postback'].get('payload'):
                            user_payload = x['postback']['payload']
        respond_back(recipient_id, user_payload,user_message)
    return "Success"


def respond_back(recipient_id,user_payload,user_message):
    """
    """
    global location
    #location = get_user_from_db(recipient_id,"location")
    if location is not "none":
        # if location has some value set the new payload
        # so that the function is executed
        user_payload = "@ShowTaco"


def Show_getStartedBtn(user_id):
    # set location to None when the bot shows the intro_message
    # db_update_document(recipient_id,["location",'none'])
    global location
    location = "none"
    intro_message = """ Hola amigo! I'm Senor botto🌮. I can show you some of the best taco restuarants in the US🍽! Just tap the button below.
                    """
    bot.send_text_message(user_id,intro_message)
    emoji_list = ['😆','😛','🙌🌮','😂','😋','😉','😜']
    x = random.randint(0,len(emoji_list)-1)
    reply_options = [("I want to eat","@taco"),(emoji_list[x],"@emoji")]
    botutils.QuickReply_SendButtons(user_id, "What do you want to do?👇", reply_options)

def AskUserLocation(recipient_id):
    # add the user to the database if the user doesnt exsit
    botutils.Ask_user_location(recipient_id)

def SearchTacoVendor(recipient_id):
    element_data_list = []
    global location
    #location = get_user_from_db(recipient_id,"location") # location is a dict
    try:
        food_data = get_food_data.yelp_search(coords=(location['long'],location['lat'])) # init with key. Done internally
        packed_results = get_food_data.get_res_info(food_data)
        if len(packed_results) == 0:
            bot.send_text_message(recipient_id,"Couldn't find anything in your area🍁(works only in the US).")
            #update the location to none
            location = "none"
            #db_update_document(recipient_id,["location","None"])
        else:
            food_data_list = []
            # building the restaurant data here and packing it into a list
            for restaurant_num in range(len(packed_results)):
                # combines cost and ratings in a string. Displayed with address
                sub_detail_str = "{0}, Ratings:{1}".format(packed_results[restaurant_num][4],
                                                            packed_results[restaurant_num][1],
                    )
                # the data is appended to the list
                food_data_list.append(
                                    {"data":
                                              (packed_results[restaurant_num][0],
                                               packed_results[restaurant_num][3],
                                               sub_detail_str,
                                               "www.google.com"),
                                       "button":["https://www.google.co.in/search?source=hp&q={}".format(packed_results[restaurant_num][0]),"Learn Now"],
                                      })

            bot.send_text_message(recipient_id,"Here's what I've found")
            ele_payload = ({
                                "element_data":food_data_list,
                            })
            botutils.generic_button_send(recipient_id,ele_payload)
            #update the location to none so that the user doesnt see this again when the start over btn is pressed
            #db_update_document(recipient_id,["location","none"])
            location = "none"
    except:
        print("returning none type")


def emoji_func(recipient_id):
    # emoji function to randomize and send emojis
    emoji_list = ['😆','😛','🙌🌮','😂','😋','😉','😜']
    x = random.randint(0,len(emoji_list)-1)
    bot.send_text_message(recipient_id,emoji_list[x])
    reply_options = [("I want to eat","@taco"),(emoji_list[x],"@emoji")]
    botutils.QuickReply_SendButtons(recipient_id, "What do you want to do?👇", reply_options)

def about_bot_func(recipient_id):
    about_info = """Senor Botto helps people to find taco restaurants in the US🌮🇺🇸.It uses Yelp API to search for restaurants in a given city. Currently Senor Botto shows restaurants that are in the US. The creator of this bot will expand to other parts of the world🙌!
    """
    bot.send_text_message(recipient_id,about_info)
    reply_options = [("I want to eat","@taco"),("Nothing","@nothing")]
    botutils.QuickReply_SendButtons(recipient_id, "What do you want to do?👇", reply_options)

def nothing_func(recipient_id):
    bot.send_text_message(recipient_id,"I'm doing nothing😵😵😜")

if __name__ == '__main__':
    app.run(debug=True,port=8080,threaded=True)
