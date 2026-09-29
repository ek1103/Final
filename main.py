import os
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, ChatMemberUpdated
from py_tgcalls import PyTgCalls
from py_tgcalls.types import MediaStream
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import yt_dlp

# ================= CONFIGURATION =================
API_ID = int(os.getenv("API_ID", "36807878"))                
API_HASH = os.getenv("API_HASH", "72e5fb566d79e6b06bf8010422be501e")           
BOT_TOKEN = os.getenv("BOT_TOKEN", "8803836538:AAE1uth6sMopO4igBAuhDS_HmGnOJAvvYm4")         
STRING_SESSION = os.getenv("STRING_SESSION", "BQHgVakAamoK-EwqaqntFH6XM-PQsmzcpu9lus6L15aSQUslc_IBiczBn4sTTEkcKIY WZiy5nx6OyFkkdzBZKd3cQSDTxppKG/TODELZilqJYb3GbUGlwqs5PBHzV7003zBOFV DtJsagDRidQd05qJeOnN7EE.JujDck2tccPFWsMm8FQNloF8_XmDG44QXVNo0aQbmmto dQm9KcGYSMXpmFldblin7AbL.Jr7qbYcwJ6POLIB6FpXWVaYSaaZLwAxzNLd2rVmOFX likqiW8WRGTYSkMX0Hp06Xo3qnZx3upqluVO-MRKKyil-dq-7PzYyL7HcQAIV4LFrmO PvvgpnZAlinrZdQAAAAGGSEHAA") 
OWNER_ID = int(os.getenv("OWNER_ID", "6554632455"))         

BRAND_LABEL = "\n\n@epic_india"

# In-Memory Storage (Restart hone par clear hoga, MongoDB production mein use karein)
ALLOWED_GROUPS = set()
AUTH_USERS = set([OWNER_ID])
CUSTOM_FILTERS = {}
WELCOME_MSG = "Welcome to the group!"
BYE_MSG = "Goodbye from the group!"

# ================= CLIENTS INITIALIZATION =================
# 1. Main Bot Client (Commands and Group Management)
app = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# 2. User Assistant Client (For Voice Chat Audio/Video streaming)
user_app = Client("user_assistant", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION)

# 3. Py-TgCalls Client (Attached with Assistant User Account)
call_app = PyTgCalls(user_app)


# ================= HELPER FUNCTIONS =================
def safe_mention(user):
    """Underscore Username Bug Fix (@e-admin-n -> @E_admin_n)"""
    if not user:
        return "Unknown"
    username = user.username
    if username:
        escaped_username = username.replace("_", "\\_")
        return f"@{escaped_username}"
    return f"[{user.first_name}](tg://user?id={user.id})"

async def send_branded_msg(chat_id, text, reply_to_message_id=None, **kwargs):
    """Sends message with mandatory Brand Label @epic_india"""
    text = f"{text}{BRAND_LABEL}"
    return await app.send_message(chat_id, text, reply_to_message_id=reply_to_message_id, **kwargs)


# ================= BOT HANDLERS =================

# 1. DM Welcome Note & Add Me Button
@app.on_message(filters.private & filters.command("start"))
async def start_private(client, message):
    text = f"This is a Private music bot made for - @epic_india{BRAND_LABEL}"
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("+ Add ME +", url=f"https://t.me/{client.me.username}?startgroup=true")]
    ])
    await message.reply_text(text, reply_markup=buttons)

# 2. Access Control: New Group Check & Allow/Deny System
@app.on_message(filters.group & filters.new_chat_members)
async def new_group_check(client, message):
    for member in message.new_chat_members:
        if member.id == client.me.id:
            chat_id = message.chat.id
            if chat_id not in ALLOWED_GROUPS:
                buttons = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("ALLOW", callback_data=f"allow_{chat_id}"),
                        InlineKeyboardButton("DENY", callback_data=f"deny_{chat_id}")
                    ]
                ])
                await client.send_message(
                    OWNER_ID, 
                    f"Bot added to group `{chat_id}` ({message.chat.title}). Grant access?", 
                    reply_markup=buttons
                )

@app.on_callback_query(filters.regex(r"^(allow|deny)_"))
async def handle_permission(client, callback_query):
    if callback_query.from_user.id != OWNER_ID:
        return await callback_query.answer("Unauthorized Action", show_alert=True)
    
    action, chat_id = callback_query.data.split("_")
    chat_id = int(chat_id)
    
    if action == "allow":
        ALLOWED_GROUPS.add(chat_id)
        await callback_query.edit_message_text(f"Group {chat_id} Access Granted.")
        await client.send_message(chat_id, f"Access Granted by Owner!{BRAND_LABEL}")
    else:
        await callback_query.edit_message_text(f"Group {chat_id} Access Denied.")
        await client.leave_chat(chat_id)

@app.on_message(filters.private & filters.command("add") & filters.user(OWNER_ID))
async def add_group_manual(client, message):
    try:
        chat_id = int(message.text.split()[1])
        ALLOWED_GROUPS.add(chat_id)
        await send_branded_msg(message.chat.id, f"Group `{chat_id}` added manually.")
    except Exception as e:
        await send_branded_msg(message.chat.id, f"Error: {e}")

# Middleware: Block unauthorized groups
@app.on_message(filters.group, group=-1)
async def group_check_middleware(client, message):
    if message.chat.id not in ALLOWED_GROUPS:
        message.stop_propagation()

# 3. URL Remover
@app.on_message(filters.group & filters.regex(r"http[s]?://"), group=1)
async def remove_urls(client, message):
    try:
        await message.delete()
    except:
        pass

# 4. Night Lock System (1 AM to 5 AM IST)
@app.on_message(filters.group, group=2)
async def night_lock(client, message):
    now = datetime.now()
    if 1 <= now.hour < 5:
        if message.media and not message.text:
            try:
                await message.delete()
                await send_branded_msg(
                    message.chat.id, 
                    f"Night mode is ON you can send after 5 A.M.\nTag: {safe_mention(message.from_user)}"
                )
            except:
                pass
            message.stop_propagation()

# 5. Help Command
@app.on_message(filters.command("help"))
async def help_cmd(client, message):
    await send_branded_msg(message.chat.id, "Contact @E_admin_n for more query")

# 6. Dynamic Welcome & Goodbye
@app.on_chat_member_updated()
async def welcome_bye_handler(client, chat_member_updated: ChatMemberUpdated):
    chat_id = chat_member_updated.chat.id
    if chat_id not in ALLOWED_GROUPS:
        return
    
    if chat_member_updated.old_chat_member is None and chat_member_updated.new_chat_member:
        user = chat_member_updated.new_chat_member.user
        await send_branded_msg(chat_id, f"{WELCOME_MSG}\nMember: {safe_mention(user)}")
        
    elif chat_member_updated.new_chat_member is None and chat_member_updated.old_chat_member:
        user = chat_member_updated.old_chat_member.user
        await send_branded_msg(chat_id, f"{BYE_MSG}\nMember: {safe_mention(user)}")

# 7. Music & Video Player (/play & /vplay) using py-tgcalls
@app.on_message(filters.command(["play", "vplay"]))
async def play_music(client, message):
    if len(message.command) < 2:
        return await send_branded_msg(message.chat.id, "Provide song name or URL.")
    
    query = " ".join(message.command[1:])
    is_video = message.command[0] == "vplay"
    
    msg = await send_branded_msg(message.chat.id, "Fetching Details...")
    
    ydl_opts = {"format": "bestaudio/best" if not is_video else "best"}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            stream_url = info['url']
            title = info['title']
            thumbnail = info['thumbnail']
        except Exception as e:
            return await msg.edit_text(f"Error finding track: {e}{BRAND_LABEL}")

    user_tag = safe_mention(message.from_user)
    
    stream = MediaStream(
        stream_url,
        video_flags=MediaStream.Flags.IGNORE if not is_video else None
    )
    
    try:
        await call_app.play(message.chat.id, stream)
        caption = f"**Title:** [{title}]({stream_url})\n**Requested By:** {user_tag}\n**User ID:** `{message.from_user.id}`{BRAND_LABEL}"
        await message.reply_photo(photo=thumbnail, caption=caption)
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"Voice Chat Error (Make sure Assistant User is in Group VC): {e}{BRAND_LABEL}")

# Stop & Leave VC Commands
@app.on_message(filters.command(["stop", "end"]) & filters.group)
async def stop_music(client, message):
    if message.from_user.id in AUTH_USERS:
        try:
            await call_app.leave_call(message.chat.id)
            await send_branded_msg(message.chat.id, "Ended voice chat stream.")
        except Exception as e:
            await send_branded_msg(message.chat.id, f"Error: {e}")

# 8. Auth Management
@app.on_message(filters.command("auth") & filters.user(OWNER_ID))
async def auth_user(client, message):
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        AUTH_USERS.add(target_id)
        await send_branded_msg(message.chat.id, f"Authorised user `{target_id}` to use voice chat")

@app.on_message(filters.command("auth_list"))
async def auth_list(client, message):
    users = "\n".join([str(u) for u in AUTH_USERS])
    await send_branded_msg(message.chat.id, f"**Auth Users List:**\n{users}")

# 9. Mass Invite (/invite - 5 users/message format)
@app.on_message(filters.command("invite") & filters.group)
async def mass_invite(client, message):
    if message.from_user.id not in AUTH_USERS:
        return
    
    members = []
    async for m in client.get_chat_members(message.chat.id):
        if not m.user.is_bot:
            members.append(safe_mention(m.user))
            
    for i in range(0, len(members), 5):
        chunk = members[i:i+5]
        text = "Come join the Voice chat!\n" + " ".join(chunk)
        await send_branded_msg(message.chat.id, text)
        await asyncio.sleep(1)

# 10. Custom Auto Replies & Word Filters
@app.on_message(filters.command("filter") & filters.group)
async def add_filter(client, message):
    if message.from_user.id not in AUTH_USERS:
        return
    
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        return await send_branded_msg(message.chat.id, "Usage: `/filter word [reply_text]` or reply to media with `/filter word`")
        
    word = args[1].lower()
    if message.reply_to_message:
        CUSTOM_FILTERS[word] = message.reply_to_message
    else:
        CUSTOM_FILTERS[word] = args[2] if len(args) > 2 else "Hi"
        
    await send_branded_msg(message.chat.id, f"Filter set for word: `{word}`")

@app.on_message(filters.command("sink") & filters.group)
async def remove_filter(client, message):
    args = message.text.split()
    if len(args) > 1 and args[1].lower() in CUSTOM_FILTERS:
        del CUSTOM_FILTERS[args[1].lower()]
        await send_branded_msg(message.chat.id, f"Off filter for `{args[1]}`")

@app.on_message(filters.group & ~filters.command(["filter", "sink"]), group=3)
async def check_filters(client, message):
    if not message.text:
        return
    word = message.text.lower()
    if word in CUSTOM_FILTERS:
        reply_target = CUSTOM_FILTERS[word]
        tag = safe_mention(message.from_user)
        if isinstance(reply_target, Message):
            await reply_target.copy(message.chat.id, reply_to_message_id=message.id)
        else:
            await send_branded_msg(message.chat.id, f"{reply_target}\nTag = {tag}", reply_to_message_id=message.id)

# 11. Safety Periodic Message (Every 10 Mins - OFF in Night Lock)
async def send_safety_message():
    now = datetime.now()
    if 1 <= now.hour < 5:
        return # Off while in night lock
        
    for chat_id in ALLOWED_GROUPS:
        try:
            await send_branded_msg(chat_id, "To stay safe Follow the rules")
        except:
            pass

scheduler = AsyncIOScheduler()
scheduler.add_job(send_safety_message, "interval", minutes=10)

# ================= MAIN RUNNER =================
async def start_all():
    print("Starting Main Bot...")
    await app.start()
    print("Starting Assistant User Account...")
    await user_app.start()
    print("Starting py-tgcalls Stream Engine...")
    await call_app.start()
    
    scheduler.start()
    print("\n✅ Epic India Music & Management Bot is fully Online!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(start_all())
