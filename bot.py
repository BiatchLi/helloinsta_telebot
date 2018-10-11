import re
import time
import telebot
import instagram_engine
import datetime
import pytz
import logging
# import settings
from telebot import util
from dbhelper import DBHelper
# from apscheduler.schedulers.background import BackgroundScheduler

# keep logs
# ===== logs ===== #
logger = telebot.logger
# telebot.logger.setLevel(logging.DEBUG)
# ----

db = DBHelper()

bot_token = ''

bot = telebot.TeleBot(token=bot_token)

# define global variables
chat_id = -1
tlgrmList = []
usersList = []
oldUsers = []
superadmins = [655045110]  # users that can use admin commands
# --------------

# main game logic for likes


def game():
    global usersList
    global tlgrmList
    global oldUsers
    try:
        roundList = list(usersList)
        usersList = []
        tlgrmList = []
        slicedList = []
        leechers = {}
        points = 0
        allUsers = oldUsers + roundList  # adding last 5 users from previous round
        # print ("All users: ", allUsers)
        for insta_data in allUsers:
            insta_username = None
            username_index = allUsers.index(insta_data)  # index in list
            if username_index < 5:  # skipping last 5 users from the previous round
                pass
            else:
                points = 0
                insta_username = (dict(insta_data).keys())
                insta_username = list(insta_username)[0]
                insta_self_id = instagram_engine.get_id(insta_username)
                offset = username_index - 5  # 5 users before
                # list of users to check for likes and comments of given id
                slicedList = allUsers[offset:username_index]
            # print(slicedList)
            for post_data in slicedList:
                print(post_data)
                post = dict(post_data).values()[0]
                shortcode = post.split('/')[4]  # instagram post id
                try:
                    commentsList = instagram_engine.get_comments(shortcode)
                    # likesList = instagram_engine.get_likes(shortcode)
                    # if str(insta_self_id) in likesList and str(insta_self_id) in commentsList:
                    if str(insta_self_id) in commentsList:
                        points += 1
                    else:
                        pass
                except Exception as e:
                    points += 1
                    print (e)
                    continue
            if points >= 1:
                pass
            else:
                if(insta_username):
                    warnings = db.get_warnings(insta_username)
                    tlgrm_id = db.get_tlgrm_id(insta_username)
                    if warnings == 5:
                        bot.kick_chat_member(chat_id, tlgrm_id)
                        db.del_tlgrm_user(tlgrm_id)  # deleting from db
                    else:
                        db.add_warning(insta_username)  # adding waring
                        leechers[insta_username] = (warnings + 1)  # adding to leechers list
        if(len(leechers) > 0):
            text = 'GROUP LEECHERS:\n\n'
            for leecher in leechers.keys():
                warnings = leechers[leecher]
                text += '<b>@' + (str(leecher) + '</b> - ' + str(warnings) + '/5 warnings\n')
            bot.send_message(chat_id, text, parse_mode='HTML')
        else:
            bot.send_message(chat_id, 'GROUP LEECHERS:\n\nIn the last 30 minutes we had no leechers!')
        oldUsers = list(allUsers[-5:])  # saving last 5 users from current round
        roundList = []
        allUsers = []
    except Exception as e:
        print (e)


#-------------------------------------------------------

# handel normal text msgs b4 game

@bot.message_handler(content_types=['text'])
def handle_text(message):
    global tlgrmList
    global usersList
    global chat_id 
    chat_id = message.chat.id
    tlgrm_id = message.from_user.id
    words = message.text.replace('\n', ' ')
    words = words.split(' ')
    # add condition here for only group
    if message.text.lower().startswith('dx5'):
        # changed here to avoid spaces
        words = [word for word in words if word != '']
        if len(words) == 3:
            insta_user = words[1].replace('@', '')
            post = words[2]
            shortcode = post.split('/')[4]
            if {insta_user: post} in usersList or {insta_user: post} in oldUsers:
                bot.delete_message(message.chat.id, message.message_id)
                text = "Dear %s, please don't flood, you are already sent your username and post." % message.from_user.first_name
                bot.send_message(message.chat.id, text, parse_mode='HTML')
            else:
                try:
                    insta_self_id = instagram_engine.get_id(insta_user)
                    post_owner_id = instagram_engine.get_post_owner(shortcode)
                    # post_comments = instagram_engine.get_comments(shortcode)
                    followers = instagram_engine.get_followers(
                        insta_user)  # followers count
                    # print ('insta_self_id',insta_self_id)
                    # print ('post_comments', post_comments)
                    # prevent swapping username and post
                    if str(insta_self_id) != str(post_owner_id):
                        bot.delete_message(message.chat.id, message.message_id)
                        text = "Dear %s, I deleted your message because the given link doesn't match to given username. Try again." % message.from_user.first_name
                        bot.send_message(
                            message.chat.id, text, parse_mode='HTML')
                    elif followers < 100:  # deleting posts with usernames that got less than 100 followers
                        bot.delete_message(message.chat.id, message.message_id)
                        text = "Dear %s, I deleted your message because you don't have enough followers." % message.from_user.first_name
                        bot.send_message(
                            message.chat.id, text, parse_mode='HTML')
                    else:
                        # preventing users from sending new username and link before 5 new from another users
                        if tlgrm_id in tlgrmList[-5:]:
                            bot.delete_message(
                                message.chat.id, message.message_id)
                            text = "Dear %s, please don't flood, you are already sent your username and post." % message.from_user.first_name
                            bot.send_message(
                                message.chat.id, text, parse_mode='HTML')
                        else:
                            #bot.pin_chat_message(message.chat.id, message.message_id)
                            tlgrmList.append(tlgrm_id)
                            usersList.append({insta_user: post})
                            check_user = db.get_tlgrm_user(tlgrm_id)
                            if check_user is None:
                                db.add_tlgrm_user(tlgrm_id, insta_user)
                            elif check_user is not None:
                                db.change_insta_user(insta_user, tlgrm_id)
                except Exception as e:
                    bot.delete_message(message.chat.id, message.message_id)
                    print (e)

        elif len(words) != 3:
            print('words len exceed 3 the words are', words)
            bot.delete_message(message.chat.id, message.message_id)
            text = "Dear %s, I deleted your message because it doesn't match the format. Please send only messages like this:\n\nDx5 <b>@username</b>\nhttps://instagram.com/p/{post-id}/" % message.from_user.first_name
            bot.send_message(message.chat.id, text, parse_mode='HTML')

    elif re.findall(r'admin.post', message.text, re.IGNORECASE) != []:  # looking for admin post
        is_admin = db.get_admin(message.from_user.id)
        if is_admin != 'none':
            pass
        else:
            bot.delete_message(message.chat.id, message.message_id)
            text = 'User trying to send admin post:\n\nFirst name: %s\nLast name: %s\nUsername: %s' % (
                message.from_user.first_name, message.from_user.last_name, message.from_user.username)
            bot.send_message(superadmins[0], text)
    elif re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                    message.text, re.IGNORECASE) != []:  # deleting all invalid format messages and foreighn links
        bot.delete_message(message.chat.id, message.message_id)
        text = "Dear %s, I deleted your message because it doesn't match the format. Please send only messages like this:\n\nDx5 <b>@username</b>\nhttps://instagram.com/p/{post-id}/" % message.from_user.first_name
        bot.send_message(message.chat.id, text, parse_mode='HTML')

# ---------------------------------------------------------------

# handeling chats

# private chat functions


@bot.message_handler(commands=['start'])
def handle_text(message):
    if message.chat.type == "private":
        text = "Hello %s! Contact @BiatchLi to join the game. or incase of recovery enter /allwarnings " % message.from_user.first_name
        bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['listcommands'])
def handle_text(message):
    if message.chat.type == "private":
        text = """ /start - start the privatechat with bot
                   /alladmins 
                   /addadmin
                   /deladmin
                   /delwarning
                   /allwarnings
                   /recovery
                     """
        bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['play'])
def handle_text(message):
    text = "game started."
    msg = bot.send_message(message.chat.id, text)
    temp = game()


@bot.message_handler(commands=['alladmins'])
def handle_text(message):
    if message.chat.type == "private" and message.from_user.id in superadmins:
        admins = db.all_admins()
        text = "All admins:\n\n"
        for admin in admins:
            if str(admin[0]) == 'none':
                pass
            else:
                text += "<b>@%s</b>\n" % (str(admin[0]))
        bot.send_message(message.from_user.id, text, parse_mode='HTML')


@bot.message_handler(commands=['addadmin'])
def handle_text(message):
    if message.chat.type == "private" and message.from_user.id in superadmins:
        text = "Send me an instagram username without @."
        msg = bot.send_message(message.chat.id, text)
        bot.register_next_step_handler(msg, add_admin)


def add_admin(message):
    global admins
    insta_user = db.get_insta_username(message.text)
    if insta_user is not None:
        tlgrm_id = db.get_tlgrm_id(insta_user)
        db.add_admin(tlgrm_id)
        bot.send_message(message.chat.id, 'Admin added!')
    else:
        bot.send_message(message.chat.id, 'Incorrect username. Try again.')


@bot.message_handler(commands=['deladmin'])
def handle_text(message):
    if message.chat.type == "private" and message.from_user.id in superadmins:
        text = "Send me an instagram username without @."
        msg = bot.send_message(message.chat.id, text)
        bot.register_next_step_handler(msg, del_admin)


def del_admin(message):
    global admins
    insta_user = db.get_insta_username(message.text)
    if insta_user is not None:
        tlgrm_id = db.get_tlgrm_id(insta_user)
        db.del_admin(tlgrm_id)
        bot.send_message(message.chat.id, 'Admin deleted!')
    else:
        bot.send_message(message.chat.id, 'Incorrect username. Try again.')


@bot.message_handler(commands=['delwarning'])
def handle_text(message):
    if message.chat.type == "private" and message.from_user.id in superadmins:
        text = "Send me an instagram username without @"
        msg = bot.send_message(message.chat.id, text)
        bot.register_next_step_handler(msg, del_warning)


def del_warning(message):
    insta_user = db.get_insta_username(message.text)
    if insta_user is not None:
        db.del_warning(insta_user)
        bot.send_message(message.chat.id, 'Warning removed!')
    else:
        bot.send_message(message.chat.id, 'Incorrect username. Try again.')


@bot.message_handler(commands=['allwarnings'])
def handle_text(message):
    if message.chat.type == "private" and message.from_user.id in superadmins:
        warnings = db.all_warnings()
        text = "All warnings:\n\n"
        for warning in warnings:
            if str(warning[0]) == 'none':
                pass
            else:
                text += "<b>@%s</b>: %s\n" % (str(warning[0]), str(warning[1]))
        splitted_text = util.split_string(text, 3000)
        for text in splitted_text:
            bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(commands=['recovery'])
def handle_text(message):
    if message.chat.type == "private":
        text = "Send me an instagram username without @"
        msg = bot.send_message(message.chat.id, text)
        bot.register_next_step_handler(msg, recover_warnings)

def recover_warnings(message):
    insta_user = db.get_insta_username(message.text)
    if insta_user is not None:
        warnings = db.get_warnings(insta_user)
        text = "Total warnings for you is %s/5 complete below tasks to get it removed :\n\n" % str(warnings)
        bot.send_message(message.chat.id, text)
        
    else:
        bot.send_message(message.chat.id, 'Incorrect username. Try again.')


# end of privatechatfunctions


#shedule game run time 

# scheduler.add_job(game, 'interval', minutes=30)  # starting round each 30 minutes
# scheduler.start()

print ("Bot started")


while True:
    try:
        bot.polling(none_stop=True)  # polling
    except Exception as e:
        logger.error(e)
        time.sleep(15)
        continue
