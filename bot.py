import os
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from dotenv import load_dotenv
import logging
from random import randint
import uuid
from database import db
import time
from threading import Thread
from flask import Flask

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_TOKEN = os.getenv("LEAKOSINT_API_TOKEN")
API_URL = os.getenv("LEAKOSINT_URL")

if not all([BOT_TOKEN, API_TOKEN, API_URL]):
    logger.error("Missing environment variables. Please check your .env file.")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN, num_threads=100)

# In-memory storage for pagination results
cache_reports = {}

# User states for admin actions
user_states = {}

# Constants for UI styling
UI_EMOJI_SEARCH = "🔍"
UI_EMOJI_RESULT = "📄"
UI_EMOJI_WARN = "⚠️"
UI_EMOJI_SUCCESS = "✅"
UI_EMOJI_WELCOME = "✨"
UI_EMOJI_PROFILE = "👤"
UI_EMOJI_MENU = "📁"
UI_EMOJI_FAQ = "❓"
UI_EMOJI_CAR = "🚗"
UI_EMOJI_ADMIN = "🛡️"
UI_EMOJI_CREDIT = "🪙"
UI_EMOJI_BLOCK = "🚫"
UI_EMOJI_TARGETED_BROADCAST = "🎯"

def get_bot_name():
    try:
        me = bot.get_me()
        return me.first_name
    except Exception:
        return "Leakosint Bot"

# --- Keyboard Generators ---

def get_main_menu_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(f"{UI_EMOJI_SEARCH} Search", callback_data="menu:search"),
        InlineKeyboardButton(f"{UI_EMOJI_PROFILE} Profile", callback_data="menu:info")
    )
    markup.row(
        InlineKeyboardButton(f"{UI_EMOJI_MENU} Menu", callback_data="menu:menu"),
        InlineKeyboardButton(f"{UI_EMOJI_CREDIT} Credits", callback_data="menu:credits")
    )
    markup.row(
        InlineKeyboardButton("💬 Contact Support", callback_data="menu:support")
    )
    return markup

def get_back_button(target="menu:main"):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("⬅️ Back", callback_data=target))
    return markup

def get_info_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("⬅️ Back", callback_data="menu:main"),
        InlineKeyboardButton("🔄 Update", callback_data="menu:info")
    )
    return markup

def get_menu_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(f"{UI_EMOJI_FAQ} Answers to questions", callback_data="menu:faq_list"),
        InlineKeyboardButton("💧 Leakage List", callback_data="menu:leakage_list")
    )
    markup.row(InlineKeyboardButton("⬅️ Back", callback_data="menu:main"))
    return markup

def get_faq_list_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("❓ How leaks occur", callback_data="faq:leaks_occur"),
        InlineKeyboardButton("🔑 Passwords", callback_data="faq:passwords_encrypted")
    )
    markup.row(
        InlineKeyboardButton("🛡️ Protection", callback_data="faq:protect_leaks"),
        InlineKeyboardButton("💧 Use of leaks", callback_data="faq:use_of_leaks")
    )
    markup.row(InlineKeyboardButton("🤨 Fake leaks", callback_data="faq:fake_leaks"))
    markup.row(InlineKeyboardButton("⬅️ Back", callback_data="menu:menu"))
    return markup

def get_admin_main_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📊 Statistics", callback_data="admin:stats"),
        InlineKeyboardButton("📢 Broadcast", callback_data="admin:broadcast_prompt")
    )
    markup.row(
        InlineKeyboardButton(f"{UI_EMOJI_TARGETED_BROADCAST} Targeted Broadcast", callback_data="admin:broadcast_targeted_prompt"),
        InlineKeyboardButton(f"{UI_EMOJI_BLOCK} Blocked Users", callback_data="admin:blocked_list")
    )
    markup.row(
        InlineKeyboardButton("👥 Manage Admins", callback_data="admin:list"),
        InlineKeyboardButton("🚫 Blacklist", callback_data="admin:blacklist_list")
    )
    markup.row(
        InlineKeyboardButton(f"{UI_EMOJI_CREDIT} Credits", callback_data="admin:credits_main"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")
    )
    return markup

def get_admin_credits_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🎁 Set Start Credits", callback_data="admin:credits_start_prompt"),
        InlineKeyboardButton("💰 Bulk Add Credits", callback_data="admin:credits_bulk_prompt")
    )
    markup.row(
        InlineKeyboardButton("👤 Manage User Credits", callback_data="admin:credits_user_prompt"),
        InlineKeyboardButton("⬅️ Back", callback_data="admin:main")
    )
    return markup

def get_admin_back_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin:main"))
    return markup

def get_admin_broadcast_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("❌ Cancel Broadcast", callback_data="admin:main"))
    return markup

# --- Content Generators ---

def get_search_content():
    return """<b>You can look for the following data:</b>
📧<b>Search by mail</b>
├ <code>arjun@gmail.com</code> - Search for mail
├ <code>amit@</code> - Search without taking into account domain
└ <code>@gmail.com</code> - Search for certain domains.

👤<b>Search by name or Nick</b>
├ <code>Arjun Malhotra</code>
├ <code>Amit Sharma</code>
├ <code>Sunil Kumar</code>
├ <code>Rahul Verma</code>
├ <code>Anjali Kumari</code>
└ <code>DesiGamer99</code>

📱<b>Search by phone number</b>
├ <code>+919876543210</code>
├ <code>9876543210</code>
└ <code>9000012345</code>

🔑<b>Password search</b>
└ <code>password123</code>

🚗<b>Search by car</b>
├ <code>TS09EA1234</code> - Search for cars in India (Example)
├ <code>MH12AB5678</code> - Search by Registration
└ <code>XTA21150053965897</code> - Search by VIN

✈️<b>Search for telegram account</b>
├ <code>Arjun Malhotra</code> - Search by name and surname
├ <code>314159265</code> - Search by ID account
└ <code>arjun_m</code> - Search by username

📘<b>Search for Facebook account</b>
├ <code>Amit Sharma</code> - Search by name
└ <code>314159265</code> - Search by ID account

🌟<b>Search for the VKontakte account</b>
├ <code>Arjun Malhotra</code> - Search by name and surname
└ <code>314159265</code> - Search by ID account

📸<b>Search for Instagram account</b>
├ <code>Anjali Kumari</code> - Search by name and surname
└ <code>314159265</code> - Search by ID account

📍<b>Search by IP</b>
└ <code>127.0.0.1</code>

📃<b>Mass search through the file. Coding UTF-8. One request on each line.</b>

<b>The composite requests in any formats are supported:</b>
├ <code>Arjun 9876543210</code> 
├ <code>Amit Sharma 127.0.0.1</code>
├ <code>Rahul Verma 02/16/1995</code>
├ <code>DesiGamer99 arjun@gmail.com</code>
├ <code>Sunil Kumar Mumbai</code>
├ <code>arjun@gmail.com password123</code>
└ <code>Anjali Kumari 16.08.1994</code>

You can also look for data at once by several requests. To do this, indicate each request on a separate line and they are executed simultaneously."""

def get_profile_content(user):
    credits = db.get_user_credits(user.id)
    return f"""<b>🆔 ID:</b> <code>{user.id}</code>
<b>{UI_EMOJI_PROFILE} Name:</b> <code>{user.first_name}</code>
<b>{UI_EMOJI_PROFILE} Surname:</b> <code>{user.last_name if user.last_name else "None"}</code>
<b>{UI_EMOJI_PROFILE} Nickname:</b> <code>@{user.username if user.username else "N/A"}</code>
<b>🪙 Credits:</b> <code>{credits}</code>"""

def get_leakage_list_content():
    return """💧 At the moment, in our bot is loaded <b>5259</b> leaks.
✏️ In total, they contain <b>93,078,578,062</b> records.
😲 This is more than in any other telegram bot!

🔎 The following data are available for the search:
📩 <b>Email:</b> 27,246,956,626
👤 <b>Full name:</b> 14,309,721,736
🔑 <b>Password:</b> 13,407,751,390
📞 <b>Telephone:</b> 12,976,487,697
👤 <b>Nick:</b> 10,931,636,063
🃏 <b>Document number:</b> 5,047,406,184
🔗 <b>Link:</b> 2,499,158,371
🆔 <b>VK ID:</b> 1,829,380,060
🎯 <b>IP:</b> 983,070,616
🏢 <b>Company:</b> 811,342,458
ⓕ <b>Facebook ID:</b> 723,518,650
🔢 <b>SSN:</b> 651,660,040
🚘 <b>Car number:</b> 524,204,448
👨 <b>Father's name:</b> 421,013,300
🃏 <b>Document:</b> 283,507,991
✈️ <b>Telegram ID:</b> 157,453,748
👾 <b>App:</b> 143,795,450
🌐 <b>Domain:</b> 84,443,741
📷 <b>Instagram ID:</b> 46,069,493"""

# --- Bot Handlers ---

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    user_id = message.from_user.id
    
    # Check if user is blocked
    if db.is_user_blocked(user_id):
        # Silently ignore or send a single notification if you want
        # For now, we follow the plan to ignore.
        return

    user_name = message.from_user.first_name
    username = message.from_user.username
    bot_name = get_bot_name()
    
    # Clear any pending states
    if user_id in user_states:
        del user_states[user_id]
        
    # Register user in DB
    db.register_user(user_id, user_name, username)
    
    welcome_text = (
        f"<b>Hello {user_name}😘</b>\n"
        f"<b>Welcome to {bot_name} 🥰</b>\n\n"
        f"🕵️ I can look for almost everything. Just send me your request."
    )
    
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=get_main_menu_keyboard())

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not db.is_admin(message.from_user.id):
        return

    text = f"{UI_EMOJI_ADMIN} <b>Admin Control Panel</b>\nWelcome, {message.from_user.first_name}."
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=get_admin_main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('menu:'))
def handle_menu_navigation(call: CallbackQuery):
    action = call.data.split(':')[1]
    
    if action == "main":
        user_name = call.from_user.first_name
        text = f"<b>Hello {user_name}😘</b>\n<b>Welcome to {get_bot_name()} 🥰</b>\n\n🕵️ I can look for almost everything. Just send me your request."
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_main_menu_keyboard())
    
    elif action == "search":
        bot.edit_message_text(get_search_content(), call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_back_button())
        
    elif action == "info":
        bot.edit_message_text(get_profile_content(call.from_user), call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_info_keyboard())
        
    elif action == "menu":
        bot.edit_message_text("🗃 <b>What are you interested in?</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_menu_keyboard())
        
    elif action == "support":
        bot.edit_message_text("💬 <b>Contact Support:</b> @flashman66", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_back_button())
        
    elif action == "credits":
        user_credits = db.get_user_credits(call.from_user.id)
        pricing_text = f"""<b>🪙 Your Balance:</b> <code>{user_credits} Credits</code>

🛡 ᴄʜᴏᴏꜱᴇ ᴀ ᴘʟᴀɴ

━━━━━━━━━━━━━━━━━━
💰 ᴄʀᴇᴅɪᴛ ᴘᴀᴄᴋs
  ⚡️ 20 ᴄʀᴇᴅɪᴛs   →  ₹85
  ⚡️ 50 ᴄʀᴇᴅɪᴛs   →  ₹155
  ⚡️ 100 ᴄʀᴇᴅɪᴛs →  ₹255
💎 ᴜɴʟɪᴍɪᴛᴇᴅ ᴘʟᴀɴs
  ✨ 7 ᴅᴀʏs  →  ₹555
  ✨ 30 ᴅᴀʏs  →  ₹2555
━━━━━━━━━━━━━━━━━━
Message the Pack / Plan to 💬 Contact Support: @flashman66"""
        bot.edit_message_text(pricing_text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_back_button())
        
    elif action == "faq_list":
        bot.edit_message_text("❓ <b>Frequently Asked Questions</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_faq_list_keyboard())
        
    elif action == "leakage_list":
        bot.edit_message_text(get_leakage_list_content(), call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_back_button("menu:menu"))

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin:'))
def handle_admin_actions(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Access Denied.")
        return

    action = call.data.split(':')[1]
    
    if action == "main":
        bot.edit_message_text(f"{UI_EMOJI_ADMIN} <b>Admin Control Panel</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_admin_main_keyboard())
        
    elif action == "stats":
        parts = call.data.split(':')
        page = int(parts[2]) if len(parts) > 2 else 0
        limit = 30
        skip = page * limit
        
        user_count = db.get_users_count()
        import math
        total_pages = math.ceil(user_count / limit) if user_count > 0 else 1
        
        text = f"📊 <b>Bot Statistics</b>\n\nTotal Users: <code>{user_count}</code>\n\n<b>Recent Users (Page {page + 1}/{total_pages}):</b>\n"
        
        users_info = db.get_all_users_info(skip=skip, limit=limit)
        for u in users_info:
            uid = u.get('user_id', 'Unknown')
            uname = u.get('username')
            fname = u.get('first_name', '')
            credits = u.get('credits', 0)
            name_display = f"@{uname}" if uname and uname != "None" else fname
            text += f"• <code>{uid}</code> - {name_display} (🪙 {credits})\n"
            
        markup = InlineKeyboardMarkup()
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin:stats:{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin:stats:{page + 1}"))
            
        if nav_buttons:
            markup.row(*nav_buttons)
            
        markup.row(InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin:main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        
    elif action == "broadcast_prompt":
        user_states[call.from_user.id] = "waiting_broadcast"
        bot.edit_message_text("📢 <b>Send the message you want to broadcast to ALL users.</b>\n\nTips:\n• You can send text, links, or emojis.\n• Type <code>/cancel</code> or click below to stop.", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_admin_broadcast_keyboard())
        
    elif action == "list":
        admins = db.get_all_admins()
        text = "👥 <b>Admins List:</b>\n\n"
        for a in admins:
            text += f"• <code>{a['user_id']}</code> (@{a['username']})\n"
        text += "\n<b>Management Commands:</b>\n"
        text += "➕ <code>/addadmin ID username</code>\n<i>(Grants admin panel access to a specific user)</i>\n\n"
        text += "➖ <code>/remadmin ID</code>\n<i>(Revokes admin privileges from a user)</i>"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_admin_back_keyboard())
        
    elif action == "blacklist_list":
        blocked = db.get_blacklist()
        text = "🚫 <b>Blacklisted Items:</b>\n\n"
        for b in blocked:
            text += f"• <code>{b['value']}</code>\n"
            
        text += "\n<b>Management Commands:</b>\n"
        text += "🔒 <code>/block value</code>\n<i>(Prevents users from querying this specific term/number)</i>\n\n"
        text += "🔓 <code>/unblock value</code>\n<i>(Removes the block, allowing it to be searched again)</i>"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_admin_back_keyboard())
    
    elif action == "broadcast_targeted_prompt":
        user_states[call.from_user.id] = "waiting_broadcast_target"
        bot.edit_message_text("🎯 <b>Targeted Broadcast</b>\n\nSend the User ID(s) you want to message, separated by commas if multiple.\n\nExample: <code>1234567, 8901234</code>", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_admin_broadcast_keyboard())

    elif action == "blocked_list":
        blocked = db.get_blocked_users()
        text = "🚫 <b>Blocked Users:</b>\n\n"
        if not blocked:
            text += "No users blocked."
        else:
            for b in blocked:
                text += f"• <code>{b['user_id']}</code> (@{b.get('username', 'N/A')}) - {b.get('first_name', 'No Name')}\n"
        
        text += "\n<b>Management Commands:</b>\n"
        text += "🔒 <code>/blockuser ID</code>\n"
        text += "🔓 <code>/unblockuser ID</code>"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_admin_back_keyboard())

    elif action == "credits_main":
        start_credits = db.get_starting_credits()
        text = f"{UI_EMOJI_CREDIT} <b>Credit Management</b>\n\nCurrent Starting Credits: <code>{start_credits}</code>"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_admin_credits_keyboard())

    elif action == "credits_start_prompt":
        user_states[call.from_user.id] = "waiting_credits_start"
        bot.edit_message_text("🎁 <b>Enter the number of credits new users should start with.</b>\nType <code>/cancel</code> to abort.", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_back_button("admin:credits_main"))

    elif action == "credits_bulk_prompt":
        user_states[call.from_user.id] = "waiting_credits_bulk"
        bot.edit_message_text("💰 <b>Enter the amount of credits to add to ALL users.</b>\nType <code>/cancel</code> to abort.", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_back_button("admin:credits_main"))

    elif action == "credits_user_prompt":
        bot.edit_message_text("👤 <b>To manage a specific user's credits, use commands:</b>\n\n➕ <code>/addcredits ID amount</code>\n<i>(Adds credits to their current balance)</i>\n\n➖ <code>/removecredits ID amount</code>\n<i>(Subtracts credits from their current balance)</i>\n\n✏️ <code>/setcredits ID amount</code>\n<i>(Overrides their old balance and sets it exactly to this number)</i>", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_back_button("admin:credits_main"))

# --- Admin Commands for Management ---

@bot.message_handler(func=lambda m: db.is_admin(m.from_user.id) and m.text.startswith('/addcredits'))
def add_credits_cmd(message):
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "Usage: <code>/addcredits ID amount</code>", parse_mode="HTML")
            return
        uid = int(parts[1])
        amt = int(parts[2])
        db.add_credits(uid, amt)
        bot.reply_to(message, f"✅ Added <code>{amt}</code> credits to user <code>{uid}</code>.", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(func=lambda m: db.is_admin(m.from_user.id) and m.text.startswith('/removecredits'))
def remove_credits_cmd(message):
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "Usage: <code>/removecredits ID amount</code>", parse_mode="HTML")
            return
        uid = int(parts[1])
        amt = int(parts[2])
        db.add_credits(uid, -amt)
        bot.reply_to(message, f"✅ Removed <code>{amt}</code> credits from user <code>{uid}</code>.", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(func=lambda m: db.is_admin(m.from_user.id) and m.text.startswith('/setcredits'))
def set_credits_cmd(message):
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "Usage: <code>/setcredits ID amount</code>", parse_mode="HTML")
            return
        uid = int(parts[1])
        amt = int(parts[2])
        # We don't have a direct set method, but we can update directly
        db.users.update_one({"user_id": uid}, {"$set": {"credits": amt}})
        bot.reply_to(message, f"✅ Set credits for <code>{uid}</code> to <code>{amt}</code>.", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(func=lambda m: db.is_admin(m.from_user.id) and m.text.startswith('/addadmin'))
def add_admin(message):
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "Usage: <code>/addadmin ID username</code>", parse_mode="HTML")
            return
        admin_id = int(parts[1])
        username = parts[2].replace("@", "")
        db.add_admin(admin_id, username)
        bot.reply_to(message, f"✅ Admin <code>{admin_id}</code> added.", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(func=lambda m: db.is_admin(m.from_user.id) and m.text.startswith('/remadmin'))
def rem_admin(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Usage: <code>/remadmin ID</code>", parse_mode="HTML")
            return
        admin_id = int(parts[1])
        db.remove_admin(admin_id)
        bot.reply_to(message, f"✅ Admin <code>{admin_id}</code> removed.", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(func=lambda m: db.is_admin(m.from_user.id) and m.text.startswith('/block'))
def block_item(message):
    parts = message.text.split(' ', 1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: <code>/block value</code>", parse_mode="HTML")
        return
    db.add_to_blacklist(parts[1].strip().lower())
    bot.reply_to(message, f"🚫 <code>{parts[1]}</code> added to blacklist.", parse_mode="HTML")

@bot.message_handler(func=lambda m: db.is_admin(m.from_user.id) and m.text.startswith('/unblock'))
def unblock_item(message):
    parts = message.text.split(' ', 1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: <code>/unblock value</code>", parse_mode="HTML")
        return
    db.remove_from_blacklist(parts[1].strip().lower())
    bot.reply_to(message, f"✅ <code>{parts[1]}</code> removed from blacklist.", parse_mode="HTML")

@bot.message_handler(func=lambda m: db.is_admin(m.from_user.id) and m.text.startswith('/blockuser'))
def block_user_cmd(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Usage: <code>/blockuser ID</code>", parse_mode="HTML")
            return
        target_id = int(parts[1])
        db.block_user(target_id)
        bot.reply_to(message, f"🚫 User <code>{target_id}</code> has been blocked.", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(func=lambda m: db.is_admin(m.from_user.id) and m.text.startswith('/unblockuser'))
def unblock_user_cmd(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Usage: <code>/unblockuser ID</code>", parse_mode="HTML")
            return
        target_id = int(parts[1])
        db.unblock_user(target_id)
        bot.reply_to(message, f"✅ User <code>{target_id}</code> has been unblocked.", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('faq:'))
def handle_faq(call: CallbackQuery):
    faq_id = call.data.split(':')[1]
    
    faq_data = {
        "leaks_occur": {
            "text": "🌐<b>Data leaks</b> most often occur due to hacking the site or server of the company.\n\nThe reason may be a vulnerability in the code, weak passwords of administrators or corruption of employees.\nAs a result of leakage, the data that the company collected about its customers fall into open access.\nThese can be tables of users with their registration data, information about orders and delivery, banking data, lists for mailings or just a history of contacts in technical support.\nIf your data is in leakage, it is already impossible to change this, except that it is possible to minimize the consequences of this for yourself.\nBut leaks of these companies are not the only way to get data into the network. There is also parsing and styllers.\nParsing is a process of automated collection of information published on the Internet.\nUnlike charming sites, Parsing is completely legal, and therefore even a legal business uses it to collect customer data and other marketing.\nUsing parsing, you can collect data from social networks, information from the forums, contact details from ads of ads and even mail and phones from password recovery forms.\nThere are also so-called styllers. These are viruses that are installed along with pirate software and steal all passwords from the list of storage of your browser, as well as other data, such as files from the desktop.\nAt the same time, the number of such hacks is calculated by billions, and the published collections weigh dozens of terabytes. If you have noticed a virus on your computer at least once, then you are in these collections.",
            "kb": get_back_button("menu:faq_list")
        },
        "passwords_encrypted": {
            "text": "🌐<b>Why are passwords encrypted?</b>\nYou could notice that in the search results, some passwords are marked as encrypted.\nIn fact, the use of the term “encryption” here is not entirely correct, the correct name of the process is a hashing. And the resulting lines are called hashs.\nThe difference is that encryption implies the possibility of decoding, and in the case of hash, no one can get a password from the hash, even the owners of the site on which you registered.\nWhen you send your password to the site, it is transformed using the sequence of actions that simply perform, but it is impossible to roll back.\nFor example, you can sort your passwords by alphabet or replace it with the amount of its numbers and after that it will be impossible to restore the original password.\nIn reality, of course, more complex algorithms are used, consisting of thousands of consecutive transformations.\nSites instead of storing your passwords, retain only the result of such a transformation. And when you enter your password, it is repeatedly transformed by the hashing algorithm and compared with preserved.\nThus, the only way to find out which password you introduced is to calculate his hash for each possible password and already among these hashs find the one that was saved on the site.\nIn the general case, this task is unreasonable, since the number of passwords is endless, and the hashing algorithms are specially selected in such a way that their calculation takes a lot of time.\nBut in reality, many users use the same password on several sites. If your password is already in leaks, then hacking his hasha will take less than a second.\nAnd even if your password is unique, there are algorithms to accelerate its selection. For example, rainbow tables. They allow you to store pre-calculated points on a certain many passwords.\nIf you save N control points from a certain set of passwords, then the search for this set will become n times faster. With the help of rainbow tables, even a password of 10 letters of different registers and numbers can be hacked in a couple of minutes.\nFor opposition to rainbow tables, the so-called \"salt\" is used. You may have noticed this field in reports. This is a random line that is added to your password before its hash. Salt can be common for all users or unique for everyone.\nThe use of salt protects against attacks through rainbow tables and through the search for the bases of previously decrypted Hashi, but it still does not protect against complete busting and hacking through leaks.\nTherefore, in order to be in relative safety, it is necessary to use an accidentally generated password longer than 10 characters on each site.",
            "kb": get_back_button("menu:faq_list")
        },
        "protect_leaks": {
            "text": "🛡️ <b>How to protect against leaks</b>\n🌐None.\nIt is impossible to protect against leaks, they were and will always be. You can only minimize the harm from them.\nYou must proceed from the fact that each letter you entered on the Internet said on the phone or wrote in documents, is already available to anyone.\nIf you want to maintain your anonymity, you need to follow some rules.\nMinimize the number of real information about yourself. More precisely, try to create a minimum number of connections between data about yourself.\nIf you indicated the mail and the phone on the same site, then this is a connection. Knowing your phone, attackers can find out your mail and vice versa.\nIf you indicated the same nickname on two different sites, this is also a connection, if the nickname is quite unique, then you can find the second site on which you used it.\nAnd so on. Using such connections, you can collect complete information about most people on open data - name, contacts, place of residence, hobbies and other data that can be used.\nTo protect yourself, find out what data about you is already in leaks and never use these mails and phones for registration anywhere again.\nUse temporary mail, disposable numbers and unique nicknames if possible. And do not give the same service several real data at once.\nTalking to the store/delivery by phone? They know your number, which means to the question \"How to contact you?\" What is a fictional name.\nUsing a taxi or delivery service? So your address is saved there. Register an account for a temporary phone number.\nAre you registering on the dating site and indicated the real name? So the mail should be temporary.\nIt is not scary if individual fragments of information about you are in open access. Real value is the connections between data that allow you to build the most complete dossier about you.\nThese tips are not a panacea, but they will greatly reduce the number of leaks of your data on the Internet.",
            "kb": get_back_button("menu:faq_list")
        },
        "use_of_leaks": {
            "text": "💧 <b>What is the use of leaks for</b>\n🌐You may be interested in why various people can use data from leaks.\nThe most harmless use is marketing. The formation of the target ausitory, clustering the base of the base by age, place of residence and income, as well as permanent advertising calls.\nCompanies do not have any problems with the law of such use of leaks, and therefore almost everyone uses them. If you do not like spam, do not indicate your main number anywhere.\nThe second very common use of leaks is the collection of information about the debtor. In case of loans in the MFI, many people indicate left -wing data, and therefore collector agencies are focused on phones and addresses from leaks.\nAlso, leaks are used to search for relatives of the debtor and, at the stage of issuing a loan, to check the reliability of the client.\nThe third use of leaks is various investigations of different levels. From the doxes “I will calculate you by ip” to serious journalistic investigations.\nThe press can also use leaks to search for compromising evidence and create scandalous publications about celebrities hobbies.\nWell, the most dangerous actions for the average person are the activities of hackers and scammers.\nWhen a new leak falls into open access, it is taken in “processing” within a few minutes. Heshi leaks are hacked, and passwords are used to enter the rest of the rest of the sites on which the victim was registered.\nIncluding mailboxes, social networks or bank accounts. At the same time, phones from leakage are called up in order to obtain codes of two -factor authentication or retelling stories about a safe account where you need to throw off the money.\nThe most actively leaks are used in the first week or two after publication, after that the data in the database in terms of validity becomes indistinguishable from earlier leaks and the value of the base for scammers falls much.\nIf you want to protect yourself from fraud, keep in your head that everyone who calls you wants to fuck you. Even if this is your boss.",
            "kb": get_back_button("menu:faq_list")
        },
        "fake_leaks": {
            "text": "🤨 <b>Fake leaks</b>\n🌐Since data leaks are a product, many people are engaged in their fake.\nThere are really a lot of fake bases, but still most leaks are real. Nevertheless, many companies affected by hacking are trying to relieve themselves of accusations, claiming that the published leak was fabricated.\nHowever, any fake leak can be distinguished from the present in various ways that will be described below. There are different ways to create a fake leak and, depending on this method, the signs that betray this are different.\n\nThe first sign that the data is fake is a small number of columns. If the database has, for example, only a name, phone and mail, this is the first bell that the data can be fabricated and you need to further study. Typically, the number of columns in leaks is more than 10. Also, fake leaks are most often in text format, and the real leaks are in the form of SQL dumps. The distant dates depend on the alleged method of fabrication.\n\n<b>1) Renaming</b>\nMost of fake leaks are made that way. From the already existing base, a piece of the desired size is cut out, called this with a random site leak and try to sell or put it in open access.\nTo calculate such a fake, break 5-10 phones from it in the bot. If the same base pops up each time, most likely the fake was made from it.\nTo simplify the work, you can immediately look for combinations of data, for example, name+phone, name+mail, phone+mail, etc.\n\n<b>2) Solyanka</b>\nMany bases are a mixture of different leaks, accidentally generated data and damaged records.\nThe easiest way to calculate the hodgepodge is to find in the database \"defective\" lines - names with English letters, random combinations of symbols, hieroglyphs, etc. To find them, you can sort data on the alphabet, the marriage will be at the beginning and at the end.\nThe likelihood that in two different bases there will be equally damaged lines are close to zero, and therefore if you look for damaged lines in leaks, you will most likely come across a donor base that participated in the creation of a hodgepodge.\nIf you cannot find damaged lines, try to find unique. To do this, through the mass search, it is possible to break through several hundred records and leave only those that were found in exactly one leak.\nHaving studied in what leaks these unique records are found, we can draw conclusions about where the data was taken in the test leak.",
            "kb": InlineKeyboardMarkup().add(InlineKeyboardButton("Next ➡️", callback_data="faq:fake_leaks_2")).add(InlineKeyboardButton("⬅️ Back", callback_data="menu:faq_list"))
        },
        "fake_leaks_2": {
            "text": "<b>3) Data change</b>\nSometimes, in order to create the illusion of fresh data, sellers change some numbers in phones, prepare random characters to posts or simply create an accidentally generated records.\nThe basis for such bases usually serves public leaks, so the above testing in the bot in the bot should be carried out in the same way for mail and name. If the creator of the base did not change them, then the fake will give out itself.\nWell, in the event that all the base columns were changed, then the data will be inconsistent with each other. That is, the checkable base will contradict all other leaks, issuing completely different information.\nThere are also bases in which only some lines are spoiled. To check such bases, it is necessary to look in other leaks at once by the combination of several columns and write out only those lines that were completely found in old leaks.\nIf the data contains passwords, try to decipher them. It usually turns out to decipher several dozen percent of passwords. If no password is deciphered, they can be generated by accident.\nIf the data always falls out in the same base, then it was she who served as a donor to create a fake.\nYou can also look for errors that often arise during the generation of chance data. For example, a name with a female name and male patronymic or vice versa, the passport in which the year of issuance (3-4 digits) does not fit with age, the TIN with an incorrect control amount, credit cards that do not satisfy the algorithm of the moon.\n\n<b>4) Incorrect data</b>\nIf the base has passed the previous two checks, you need to make sure that this is the site that is written in the name.\nHackers may well hack the register of homeless homework in St. Petersburg, and then sell it under the guise of a list of buyers of Lamborghini.\nThe easiest way to check whether the real source is through the form of password restoration on the site, which was supposedly hacked. Go to the site and try to restore the password using mail or phone from the database.\nMany sites will write that mail/phone is not registered. If you checked several records from the base and they are not all registered on the site, then the source of the base is different.\nPlease note that some sites send a verification code regarding whether such a person is registered. In this case, you can try instead of sending a password to be registered with one of the posts in the database to check if it is already registered.\nHowever, many sites may no longer work or not have appropriate forms. In this case, you can look for the data that should be on the site in the audited database.\nTo do this, you can find this site in the NAZ.api collection and look for the mail and nicknames from there, you can take nicknames from the site or from its web archive.\nIt also makes sense in the database itself to look for the name of the site or a link to it, as well as the adjustment of HTTP and HTTPS. Links can give out what source a leak is really taken from, especially if the base in SQL format.\nIt is also worth checking the dates in the leak. If the hacking date is known, then the latest date/entrance date in the leak should derive around this time. You can check the oldest registration dates in the database. If they are several years older than the site itself or its first references in the web archive, then the source is most likely different.",
            "kb": get_back_button("faq:fake_leaks")
        }
    }
    
    if faq_id in faq_data:
        bot.edit_message_text(faq_data[faq_id]["text"], call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=faq_data[faq_id]["kb"])

# --- Search Handling ---

def generate_report(query, query_id):
    """
    Fetches data from Leakosint API and formats it into pages for Telegram.
    """
    global cache_reports
    data = {
        "token": API_TOKEN,
        "request": query.strip(),
        "limit": 300,
        "lang": "en"
    }
    
    try:
        response = requests.post(API_URL, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        logger.info(f"API Response for '{query}': {result}")
        
        if "Error code" in result:
            logger.error(f"API returned error: {result['Error code']}")
            return None, False

        pages = []
        found_results = False
        if "List" in result:
            for db_name, db_data in result["List"].items():
                if db_name == "No results found":
                    continue
                
                found_results = True
                content = [f"<b>{UI_EMOJI_RESULT} Source: {db_name}</b>", ""]
                
                if "InfoLeak" in db_data:
                    content.append(f"<i>{db_data['InfoLeak']}</i>")
                    content.append("")
                
                if "Data" in db_data:
                    for entry in db_data["Data"]:
                        entry_text = []
                        for key, value in entry.items():
                            entry_text.append(f"<b>{key}:</b> <code>{value}</code>")
                        content.append("\n".join(entry_text))
                        content.append("-" * 20)
                
                full_text = "\n".join(content)
                if len(full_text) > 3800:
                    pages.append(full_text[:3800] + "\n\n<i>Long result truncated...</i>")
                else:
                    pages.append(full_text)
        
        if not pages:
            pages = [f"{UI_EMOJI_WARN} <b>No results found for your query.</b>"]
            
        # Prevent memory leak under high usage
        if len(cache_reports) > 500:
            cache_reports.pop(next(iter(cache_reports)))
            
        cache_reports[str(query_id)] = {"pages": pages, "found": found_results}
        return pages, found_results

    except Exception as e:
        logger.error(f"Error calling API: {e}")
        return None, False

def create_keyboard(query_id, page_index, total_pages):
    markup = InlineKeyboardMarkup()
    if total_pages <= 1:
        markup.add(InlineKeyboardButton("🏠 Back to Menu", callback_data="menu:main"))
        return markup

    prev_index = (page_index - 1) % total_pages
    next_index = (page_index + 1) % total_pages
    
    markup.row(
        InlineKeyboardButton(text="⬅️ Previous", callback_data=f"page:{query_id}:{prev_index}"),
        InlineKeyboardButton(text=f"{page_index + 1} / {total_pages}", callback_data="none"),
        InlineKeyboardButton(text="Next ➡️", callback_data=f"page:{query_id}:{next_index}")
    )
    markup.add(InlineKeyboardButton("🏠 Back to Menu", callback_data="menu:main"))
    return markup

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    user_id = message.from_user.id
    
    # Check if user is blocked
    if db.is_user_blocked(user_id):
        return

    # Handle /cancel
    if message.text == "/cancel":
        if user_id in user_states:
            del user_states[user_id]
            bot.reply_to(message, "Action cancelled.")
        return

    # Handle states
    if user_id in user_states:
        state = user_states[user_id]
        
        # If it's a command, abort the state
        if message.text.startswith('/'):
            del user_states[user_id]
            return

        if state == "waiting_broadcast":
            del user_states[user_id]
            users = db.get_all_user_ids()
            success_count = 0
            for uid in users:
                if db.is_user_blocked(uid):
                    continue
                try:
                    bot.send_message(uid, f"📢 <b>Announcement</b>\n\n{message.text}", parse_mode="HTML")
                    success_count += 1
                    time.sleep(0.05)
                except Exception:
                    pass
            bot.reply_to(message, f"✅ Broadcast sent to <code>{success_count}</code> users.")
            return
        
        elif state == "waiting_broadcast_target":
            targets = [t.strip() for t in message.text.split(',')]
            valid_targets = []
            for t in targets:
                if t.isdigit():
                    valid_targets.append(int(t))
            
            if not valid_targets:
                bot.reply_to(message, "❌ No valid User IDs found. Action cancelled.")
                del user_states[user_id]
                return
                
            user_states[user_id] = {"state": "waiting_broadcast_message_targeted", "targets": valid_targets}
            bot.reply_to(message, f"🎯 Targets set: <code>{len(valid_targets)}</code> users.\n\nNow send the <b>message</b> you want to broadcast to them.", parse_mode="HTML", reply_markup=get_admin_broadcast_keyboard())
            return

        elif isinstance(user_states[user_id], dict) and user_states[user_id].get("state") == "waiting_broadcast_message_targeted":
            targets = user_states[user_id]["targets"]
            broadcast_text = message.text
            del user_states[user_id]
            
            success_count = 0
            for uid in targets:
                if db.is_user_blocked(uid):
                    continue
                try:
                    bot.send_message(uid, f"📢 <b>Important Message</b>\n\n{broadcast_text}", parse_mode="HTML")
                    success_count += 1
                    time.sleep(0.05)
                except Exception:
                    pass
            bot.reply_to(message, f"✅ Targeted broadcast sent to <code>{success_count}</code> / {len(targets)} users.")
            return

        elif state == "waiting_credits_start":
            try:
                amt = int(message.text)
                db.set_starting_credits(amt)
                del user_states[user_id]
                bot.reply_to(message, f"✅ Starting credits set to <code>{amt}</code>.")
            except ValueError:
                bot.reply_to(message, "❌ Please enter a valid number.")
            return

        elif state == "waiting_credits_bulk":
            try:
                amt = int(message.text)
                db.bulk_add_credits(amt)
                del user_states[user_id]
                bot.reply_to(message, f"✅ Added <code>{amt}</code> credits to ALL users.")
            except ValueError:
                bot.reply_to(message, "❌ Please enter a valid number.")
            return

    # --- Credit Check ---
    user_credits = db.get_user_credits(user_id)
    if user_credits <= 0 and not db.is_admin(user_id):
        no_credits_text = (
            f"❌ <b>You don't have enough credits!</b>\n\n"
            f"You have used up all your free credits. To purchase more, please contact our support:\n"
            f"💬 @flashman66"
        )
        bot.reply_to(message, no_credits_text, parse_mode="HTML")
        return

    # Default to search logic
    query_text = message.text
    
    # Check blacklist
    if db.is_blacklisted(query_text):
        bot.reply_to(message, "⚠️ <b>Administrator blocked this details.</b>", parse_mode="HTML")
        return

    query_id = uuid.uuid4().hex[:8]
    status_msg = bot.reply_to(message, f"{UI_EMOJI_SEARCH} Searching for <code>{query_text}</code>...", parse_mode="HTML")
    
    report_pages, found_results = generate_report(query_text, query_id)
    
    if report_pages is None:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text=f"{UI_EMOJI_WARN} <b>An error occurred while fetching data.</b> Please try again later.",
            parse_mode="HTML",
            reply_markup=get_back_button()
        )
        return

    # --- Deduct Credit only if successful ---
    if found_results and not db.is_admin(user_id):
        db.deduct_credit(user_id)
        new_credits = user_credits - 1
        # Optionally show credit remainder in footer
        report_pages[0] += f"\n\n<i>(🪙 Credits remaining: {new_credits})</i>"

    markup = create_keyboard(query_id, 0, len(report_pages))
    
    try:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text=report_pages[0],
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception:
        clean_text = report_pages[0].replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "").replace("<code>", "").replace("</code>", "")
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text=clean_text,
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('page:'))
def handle_pagination(call: CallbackQuery):
    _, query_id, page_index = call.data.split(':')
    page_index = int(page_index)
    
    if query_id not in cache_reports:
        bot.answer_callback_query(call.id, "Session expired. Please search again.", show_alert=True)
        return

    report_data = cache_reports[query_id]
    report_pages = report_data["pages"]
    total_pages = len(report_pages)
    markup = create_keyboard(query_id, page_index, total_pages)
    
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=report_pages[page_index],
            parse_mode="HTML",
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)
    except Exception:
        bot.answer_callback_query(call.id, "Error switching pages.")

# --- Render Free Tier Keep-Alive ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    logger.info("Bot is starting...")
    # Start web server in a separate thread for Render free tier
    web_thread = Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()
    bot.infinity_polling()
