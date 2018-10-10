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
# add bot token here
bot_token = ''

bot = telebot.TeleBot(token=bot_token)

# define global variables
chat_id = -1
tlgrmList = []
usersList = []
oldUsers = []
superadmins = [655045110]  # users that can use admin commands
# --------------


# handeling chats

# private chat functions


@bot.message_handler(commands=['start'])
def handle_text(message):
    if message.chat.type == "private":
        text = "Hello %s! Contact @bohdan_antonov to join the game." % message.from_user.first_name
        bot.send_message(tlgrm_id, text)


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

# end of privatechatfunctions

# handel normal text msgs b4 game


@bot.message_handler(content_types=['text'])
def handle_text(message):
    global tlgrmList
    global usersList
    tlgrm_id = message.from_user.id
    words = message.text.replace('\n', ' ')
    words = words.split(' ')
    # add condition here for only group
    if message.text.lower().startswith('dx5'):
        if len(words) == 3:
            insta_user = words[1].replace('@', '')
            post = words[2]
            shortcode = post.split('/')[4]
            if {insta_user: post} in usersList or {insta_user: post} in oldUsers:
                bot.delete_message(message.chat.id, message.message_id)
            else:
                try:
                    insta_self_id = instagram_engine.get_id(insta_user)
                    post_owner_id = instagram_engine.get_post_owner(shortcode)
                    followers = instagram_engine.get_followers(insta_user)  # followers count
                    print (followers)
                    if str(insta_self_id) != str(post_owner_id):  # prevent swapping username and post
                        bot.delete_message(message.chat.id, message.message_id)
                        text = "Dear %s, I deleted your message because the given link doesn't match to given username. Try again." % message.from_user.first_name
                        bot.send_message(message.chat.id, text, parse_mode='HTML')
                    elif followers < 100:  # deleting posts with usernames that got less than 100 followers
                        bot.delete_message(message.chat.id, message.message_id)
                        text = "Dear %s, I deleted your message because you don't have enough followers." % message.from_user.first_name
                        bot.send_message(message.chat.id, text, parse_mode='HTML')
                    else:
                        if tlgrm_id in tlgrmList[-5:]:  # preventing users from sending new username and link before 5 new from another users
                            bot.delete_message(message.chat.id, message.message_id)
                            text = "Dear %s, please don't flood, you are already sent your username and post." % message.from_user.first_name
                            bot.send_message(message.chat.id, text, parse_mode='HTML')
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
        #elif len(words) != 3:
            #bot.delete_message(message.chat.id, message.message_id)
            #text = "Dear %s, I deleted your message because it doesn't match the format. Please send only messages like this:\n\nDx5 <b>@username</b>\nhttps://instagram.com/p/{post-id}/" % message.from_user.first_name
            #bot.send_message(message.chat.id, text, parse_mode='HTML')
    elif re.findall(r'admin.post', message.text, re.IGNORECASE) != []:  # looking for admin post
        is_admin = db.get_admin(message.from_user.id)
        if is_admin != 'none':
            pass
        else:
            bot.delete_message(message.chat.id, message.message_id)
            text = 'User trying to send admin post:\n\nFirst name: %s\nLast name: %s\nUsername: %s' % (message.from_user.first_name, message.from_user.last_name, message.from_user.username)
            bot.send_message(superadmins[0], text)
    elif re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                    message.text, re.IGNORECASE) != []:  # deleting all invalid format messages and foreighn links
        bot.delete_message(message.chat.id, message.message_id)
        #text = "Dear %s, I deleted your message because it doesn't match the format. Please send only messages like this:\n\nDx5 <b>@username</b>\nhttps://instagram.com/p/{post-id}/" % message.from_user.first_name
        #bot.send_message(message.chat.id, text, parse_mode='HTML')

# ---------------------------------------------------------------

# # testing functions here

# hendeling normal msgs


# def find_at(msg):
#     for text in msg:
#         if '//' in text:
#             return text


# @bot.message_handler(commands=['start'])
# def ask_to_join(message):
#     if message.chat.type == "private":
#         text = "Hello %s! Contact @BiatchLi to join the game." % message.from_user.first_name
#         bot.reply_to(message, text)

# @bot.message_handler(commands=['setup'])
# def ask_to_join(message):
#     if message.chat.type == "private":
#         text = "setting up db"
#         db.setup()
#         bot.reply_to(message, text)

# @bot.message_handler(commands=['fetch'])
# def ask_to_join(message):
#     if message.chat.type == "private":
#         text = "fetching db"
#         db.fetch_me()
#         bot.reply_to(message, text)

# @bot.message_handler(commands=['insert_dumy'])
# def ask_to_join(message):
#     if message.chat.type == "private":
#         text = "insering dumy"
#         db.insert_dumy()
#         bot.reply_to(message, text)

# @bot.message_handler(commands=['alladmins'])
# def handle_text(message):
#     if message.chat.type == "private" and message.from_user.id in superadmins:
#         admins = db.all_admins()
#         text = "All admins:\n\n"
#         for admin in admins:
#             if str(admin[0]) == 'none':
#                 pass
#             else:
#                 text += "<b>@%s</b>\n" % (str(admin[0]))
#         bot.send_message(message.from_user.id, text, parse_mode='HTML')

# @bot.message_handler(commands=['addadmin'])
# def handle_text(message):
#     if message.chat.type == "private" and message.from_user.id in superadmins:
#         text = "Send me an instagram username without @."
#         msg = bot.send_message(message.chat.id, text)
#         bot.register_next_step_handler(msg, add_admin)


# def add_admin(message):
#     global admins
#     insta_user = db.get_insta_username(message.text)
#     if insta_user is not None:
#         tlgrm_id = db.get_tlgrm_id(insta_user)
#         db.add_admin(tlgrm_id)
#         bot.send_message(message.chat.id, 'Admin added!')
#     else:
#         bot.send_message(message.chat.id, 'Incorrect username. Try again.')


# @bot.message_handler(content_types=['text'])
# def handle_text(message):
#     global tlgrmList
#     global usersList
#     if message.chat.type == "private":
#         tlgrm_id = message.from_user.id
#         words = message.text.replace('\n', ' ')
#         words = words.split(' ')
#     # text = "text type testing"
#     bot.reply_to(message, words[1])

# end

# @bot.message_handler(commands=['help'])
# def send_welcome(message):
#     bot.reply_to(message, 'to use this bot ,send it a username')


# @bot.message_handler(commands=['test'])
# def send_welcome(message):
#     print(usersList)
#     # usersList = (message.from_user.id)
#     # game()
#     bot.reply_to(message, usersList)


# @bot.message_handler(func=lambda msg: msg.text is not None and '//' in msg.text)
# def at_answer(message):
#     texts = message.text.split()
#     at_text = find_at(texts)
#     bot.reply_to(message, 'https://instagram.com/{}'.format(at_text[1:]))


while True:
    try:
        bot.polling(none_stop=True)  # polling
    except Exception as e:
        logger.error(e)
        time.sleep(15)
        continue
