"""
🔥 ULTRA ADVANCED TELEGRAM USERBOT 🔥
⚠️ String Session Based - No Phone Number Needed!
Features: Auto Forward, Advanced Spam, Filters, Scraping, Mass Actions
"""

import asyncio
import re
import sqlite3
import random
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pyrogram import Client, filters, idle
from pyrogram.types import Message, User
from pyrogram.errors import FloodWait, UserNotParticipant, PeerIdInvalid, ChatAdminRequired
from pyrogram.enums import ChatType, ChatMemberStatus

# ===================== CONFIGURATION =====================
API_ID = int(os.getenv("API_ID", "24116223"))  # Get from environment
API_HASH = os.getenv("API_HASH", "01ee4ca922fcd18c4e20afcc56bbac07")
STRING_SESSION = os.getenv("STRING_SESSION", "BQE1hZwAtPqd9nfrmMEsCkwJ4GiXCC4Dj119Ioy2Va4SUjQlwS5B30ZAePIQhfDmSNU1qfiR1N5hY27CvJemmAh1MeTtPflbWrKiS3AGwcCt24ncynNuGsAPgqHeqWfxb00TcUjBw8w6eRc7R6-45JgT75S-9IKp_M4ZZHDt3XjRaJQ5zTE9RL3kFVIdzjRXw1-pHqdzkAN6D8qUzn4zgQH7sJoMhLAMfRl2oglgmja7XLCvLl2CPky0vdcnuFry9QPqOsx9fm3zacXbg-9B4jJydgH6U9WHpTZQldwm-saVuIxK7pwgpJd_pYUaQn4zI0DucFEgQUsVTt8i7dq7E3kh2vnM2gAAAAH6VzCVAA")  # Your string session here

# Admin IDs (Bot owners)
ADMIN_IDS = [8494985365]  # Replace with your user ID

# Database
DB_NAME = "advanced_userbot.db"

# ===================== DATABASE SETUP =====================

def init_db():
    """Initialize SQLite database with all tables"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        is_premium INTEGER DEFAULT 0,
        is_blocked INTEGER DEFAULT 0,
        spam_delay REAL DEFAULT 2.0,
        spam_count INTEGER DEFAULT 10,
        random_mode INTEGER DEFAULT 0,
        auto_forward INTEGER DEFAULT 1,
        filter_enabled INTEGER DEFAULT 0,
        repost_mode INTEGER DEFAULT 0,
        header TEXT,
        footer TEXT,
        caption_mode INTEGER DEFAULT 0,
        link_remove INTEGER DEFAULT 0,
        replace_text TEXT
    )
    ''')
    
    # Forward pairs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS forward_pairs (
        pair_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        source_id INTEGER,
        dest_id INTEGER,
        UNIQUE(user_id, source_id, dest_id)
    )
    ''')
    
    # Spam messages
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS spam_messages (
        msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message_id INTEGER,
        chat_id INTEGER,
        text TEXT,
        UNIQUE(user_id, message_id, chat_id)
    )
    ''')
    
    # Filter words
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS filters (
        filter_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        word TEXT,
        action TEXT DEFAULT 'skip',
        UNIQUE(user_id, word)
    )
    ''')
    
    # Scraped members
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scraped_members (
        scrape_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        chat_id INTEGER,
        member_id INTEGER,
        username TEXT,
        first_name TEXT,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, chat_id, member_id)
    )
    ''')
    
    # Auto reactions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS auto_reactions (
        reaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        chat_id INTEGER,
        reaction TEXT,
        UNIQUE(user_id, chat_id)
    )
    ''')
    
    # Statistics
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stats (
        user_id INTEGER PRIMARY KEY,
        messages_forwarded INTEGER DEFAULT 0,
        messages_spammed INTEGER DEFAULT 0,
        members_scraped INTEGER DEFAULT 0,
        reactions_sent INTEGER DEFAULT 0,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

# ===================== DATABASE HELPERS =====================

def get_db():
    return sqlite3.connect(DB_NAME)

def get_user_settings(user_id):
    """Get user settings, create if not exists"""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
    
    conn.close()
    return dict(user) if user else {}

def update_setting(user_id, key, value):
    """Update user setting"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()

def update_stat(user_id, stat_key, increment=1):
    """Update statistics"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        INSERT INTO stats (user_id, {stat_key}) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET {stat_key} = {stat_key} + ?
    """, (user_id, increment, increment))
    conn.commit()
    conn.close()

# ===================== UTILITY FUNCTIONS =====================

def is_admin(user_id):
    return user_id in ADMIN_IDS

def is_premium(user_id):
    settings = get_user_settings(user_id)
    return settings.get('is_premium', 0) == 1

def get_limit(user_id, limit_type):
    """Get user limits based on premium status"""
    limits = {
        'forward_pairs': (50, 500),
        'spam_count': (50, 1000),
        'scrape_limit': (1000, 50000)
    }
    is_prem = is_premium(user_id)
    return limits.get(limit_type, (10, 100))[1 if is_prem else 0]

def extract_username(text):
    """Extract username/channel from various formats"""
    patterns = [
        r't\.me/([a-zA-Z0-9_]+)',
        r'telegram\.me/([a-zA-Z0-9_]+)',
        r'@([a-zA-Z0-9_]+)',
        r'^([a-zA-Z0-9_]+)$'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def remove_links(text):
    """Remove all links from text"""
    patterns = [
        r'https?://\S+',
        r't\.me/\S+',
        r'@\w+',
        r'\[.*?\]\(.*?\)'  # Markdown links
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text)
    return text.strip()

# ===================== CLIENT INITIALIZATION =====================
if not STRING_SESSION:
    print("❌ STRING_SESSION environment variable not set!")
    exit(1)

app = Client(
    "advanced_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=STRING_SESSION
)

# ===================== START & HELP COMMANDS =====================

HELP_TEXT = """
🔥 **ULTRA ADVANCED USERBOT** 🔥

**📢 FORWARDING MODULE:**
`/addpair <source> <dest>` - Add forward pair
`/delpair <source> <dest>` - Delete pair
`/listpairs` - List all pairs
`/clearpairs` - Clear all pairs
`/toggle <setting>` - Toggle: auto, filter, repost, caption, linkremove

**💬 SPAM MODULE:**
`/setmsg` (reply to message) - Add to spam list
`/listmsgs` - Show spam messages
`/clearmsg` - Clear spam list
`/setcount <num>` - Set spam count
`/setdelay <sec>` - Set delay
`/startspam <target> [count]` - Start spamming
`/stopspam` - Stop spam

**🎯 ADVANCED SPAM:**
`/randomspam <target>` - Random order spam
`/burstspam <target>` - High speed spam (Premium)
`/timespam <target> <time>` - Timed spam (5m, 1h, etc)

**📝 MESSAGE EDITING:**
`/setheader <text>` - Set message header
`/setfooter <text>` - Set message footer
`/replace <old>|<new>` - Replace text in messages

**🔍 FILTER MODULE:**
`/filter add <word>` - Add filter word
`/filter remove <word>` - Remove filter
`/filter list` - List filters
`/filter action <skip|delete>` - Set filter action

**👥 SCRAPER MODULE:**
`/scrape <chat>` - Scrape members
`/scraped` - View scraped list
`/export` - Export to file
`/addscraped <target>` - Add all to group

**🤖 AUTO ACTIONS:**
`/autoreact <chat> <emoji>` - Auto react to messages
`/stopreact <chat>` - Stop auto react
`/listreact` - List auto reactions
`/autopromote <chat>` - Auto promote members
`/autopin <chat>` - Auto pin messages

**📊 MASS ACTIONS:**
`/massadd <target> <count>` - Mass add members
`/massmsg <target>` - Mass DM members
`/masskick <chat>` - Kick all members (Admin)
`/massban <chat>` - Ban all members (Admin)

**📈 STATS & INFO:**
`/stats` - Your statistics
`/info <username>` - User info
`/chatinfo <chat>` - Chat details
`/members <chat>` - Member count

**⚙️ SETTINGS:**
`/settings` - View all settings
`/reset` - Reset all settings
`/premium` - Premium info

**🔐 ADMIN COMMANDS:**
`/broadcast` - Broadcast message
`/block <user_id>` - Block user
`/unblock <user_id>` - Unblock user
`/givepremium <user_id>` - Give premium
`/revoke <user_id>` - Revoke premium
`/globalstats` - Global statistics

**🎨 FUN FEATURES:**
`/spam5 <target>` - 5 different templates spam
`/emojiraid <target> <emoji>` - Emoji spam
`/typewriter <text>` - Typewriter effect
`/rainbow <text>` - Rainbow text animation

**⚡ QUICK COMMANDS:**
`/q <text>` - Quick spam (10 times)
`/qq <text>` - Super quick spam (50 times)
`/qqq <text>` - Ultra spam (100 times)
"""

@app.on_message(filters.command("start", prefixes="/") & filters.me)
async def start_command(client, message):
    status = "🎁 **PREMIUM**" if is_premium(message.from_user.id) else "🆓 **FREE**"
    await message.edit(
        f"🤖 **USERBOT ACTIVE!**\n\n"
        f"Status: {status}\n"
        f"Version: 2.0 Advanced\n\n"
        f"Use `/help` for commands!"
    )

@app.on_message(filters.command("help", prefixes="/") & filters.me)
async def help_command(client, message):
    await message.edit(HELP_TEXT, disable_web_page_preview=True)

# ===================== FORWARDING MODULE =====================

@app.on_message(filters.command("addpair", prefixes="/") & filters.me)
async def add_pair(client, message):
    user_id = message.from_user.id
    
    if len(message.command) < 3:
        await message.edit("⚠️ Usage: `/addpair @source @destination`")
        return
    
    _, source, dest = message.text.split(None, 2)
    source_user = extract_username(source)
    dest_user = extract_username(dest)
    
    if not source_user or (dest.lower() != 'me' and not dest_user):
        await message.edit("❌ Invalid source/destination!")
        return
    
    await message.edit(f"🔍 Adding pair...")
    
    try:
        source_chat = await client.get_chat(source_user)
        dest_id = user_id if dest.lower() == 'me' else (await client.get_chat(dest_user)).id
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO forward_pairs (user_id, source_id, dest_id) VALUES (?, ?, ?)",
            (user_id, source_chat.id, dest_id)
        )
        conn.commit()
        
        if conn.total_changes > 0:
            await message.edit(
                f"✅ **Pair Added!**\n\n"
                f"From: `{source_chat.title}`\n"
                f"To: `{dest_id}`"
            )
        else:
            await message.edit("⚠️ Pair already exists!")
        conn.close()
    except Exception as e:
        await message.edit(f"❌ Error: `{str(e)}`")

@app.on_message(filters.command("listpairs", prefixes="/") & filters.me)
async def list_pairs(client, message):
    user_id = message.from_user.id
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT source_id, dest_id FROM forward_pairs WHERE user_id = ?", (user_id,))
    pairs = cursor.fetchall()
    conn.close()
    
    if not pairs:
        await message.edit("📭 No pairs added!")
        return
    
    text = "📋 **YOUR FORWARDING PAIRS:**\n\n"
    for idx, (src, dst) in enumerate(pairs, 1):
        try:
            src_title = (await client.get_chat(src)).title
            dst_title = "Saved Messages" if dst == user_id else (await client.get_chat(dst)).title
            text += f"{idx}. `{src_title}` ➡️ `{dst_title}`\n"
        except:
            text += f"{idx}. `{src}` ➡️ `{dst}`\n"
    
    await message.edit(text)

# ===================== SPAM MODULE =====================

@app.on_message(filters.command("setmsg", prefixes="/") & filters.me & filters.reply)
async def set_spam_msg(client, message):
    user_id = message.from_user.id
    replied = message.reply_to_message
    
    conn = get_db()
    cursor = conn.cursor()
    
    text = replied.text or replied.caption or "[Media]"
    cursor.execute(
        "INSERT OR IGNORE INTO spam_messages (user_id, message_id, chat_id, text) VALUES (?, ?, ?, ?)",
        (user_id, replied.id, replied.chat.id, text[:100])
    )
    conn.commit()
    conn.close()
    
    await message.edit("✅ Message saved to spam list!")

@app.on_message(filters.command("startspam", prefixes="/") & filters.me)
async def start_spam(client, message):
    user_id = message.from_user.id
    
    if len(message.command) < 2:
        await message.edit("⚠️ Usage: `/startspam @target [count]`")
        return
    
    target = extract_username(message.command[1])
    count = int(message.command[2]) if len(message.command) > 2 else 1
    
    try:
        target_chat = await client.get_chat(target)
    except Exception as e:
        await message.edit(f"❌ Error: `{str(e)}`")
        return
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT message_id, chat_id FROM spam_messages WHERE user_id = ?", (user_id,))
    messages = cursor.fetchall()
    conn.close()
    
    if not messages:
        await message.edit("❌ No spam messages! Use `/setmsg` first.")
        return
    
    settings = get_user_settings(user_id)
    spam_count = settings['spam_count']
    delay = settings['spam_delay']
    
    await message.edit(f"🎯 Starting spam to `{target_chat.title}`...")
    
    sent = 0
    for _ in range(count):
        for msg_id, chat_id in messages:
            for _ in range(spam_count):
                try:
                    await client.copy_message(target_chat.id, chat_id, msg_id)
                    sent += 1
                    update_stat(user_id, 'messages_spammed')
                    await asyncio.sleep(delay)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                except:
                    pass
    
    await message.edit(f"✅ Spam completed! Sent: {sent} messages")

# ===================== SCRAPER MODULE =====================

@app.on_message(filters.command("scrape", prefixes="/") & filters.me)
async def scrape_members(client, message):
    user_id = message.from_user.id
    
    if len(message.command) < 2:
        await message.edit("⚠️ Usage: `/scrape @groupusername`")
        return
    
    target = extract_username(message.command[1])
    await message.edit(f"🔍 Scraping members from `{target}`...")
    
    try:
        chat = await client.get_chat(target)
        
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await message.edit("❌ This is not a group!")
            return
        
        conn = get_db()
        cursor = conn.cursor()
        
        scraped_count = 0
        async for member in client.get_chat_members(chat.id):
            if member.user.is_bot:
                continue
            
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO scraped_members (user_id, chat_id, member_id, username, first_name) VALUES (?, ?, ?, ?, ?)",
                    (user_id, chat.id, member.user.id, member.user.username, member.user.first_name)
                )
                if conn.total_changes > 0:
                    scraped_count += 1
                    
                if scraped_count % 100 == 0:
                    await message.edit(f"🔍 Scraped: {scraped_count} members...")
            except:
                pass
        
        conn.commit()
        conn.close()
        
        update_stat(user_id, 'members_scraped', scraped_count)
        await message.edit(f"✅ Scraped {scraped_count} members from `{chat.title}`!")
        
    except Exception as e:
        await message.edit(f"❌ Error: `{str(e)}`")

@app.on_message(filters.command("scraped", prefixes="/") & filters.me)
async def view_scraped(client, message):
    user_id = message.from_user.id
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM scraped_members WHERE user_id = ?",
        (user_id,)
    )
    count = cursor.fetchone()[0]
    
    cursor.execute(
        "SELECT DISTINCT chat_id FROM scraped_members WHERE user_id = ?",
        (user_id,)
    )
    chats = cursor.fetchall()
    conn.close()
    
    text = f"📊 **SCRAPED MEMBERS:**\n\nTotal: {count} members\nFrom {len(chats)} chats\n\n"
    
    for (chat_id,) in chats[:10]:
        try:
            chat = await client.get_chat(chat_id)
            text += f"• `{chat.title}`\n"
        except:
            text += f"• `{chat_id}`\n"
    
    await message.edit(text)

# ===================== MASS ACTIONS =====================

@app.on_message(filters.command("massadd", prefixes="/") & filters.me)
async def mass_add(client, message):
    user_id = message.from_user.id
    
    if len(message.command) < 3:
        await message.edit("⚠️ Usage: `/massadd @target <count>`")
        return
    
    target = extract_username(message.command[1])
    count = int(message.command[2])
    
    try:
        target_chat = await client.get_chat(target)
    except Exception as e:
        await message.edit(f"❌ Error: `{str(e)}`")
        return
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT member_id FROM scraped_members WHERE user_id = ? LIMIT ?",
        (user_id, count)
    )
    members = cursor.fetchall()
    conn.close()
    
    if not members:
        await message.edit("❌ No scraped members! Use `/scrape` first.")
        return
    
    await message.edit(f"➕ Adding {len(members)} members to `{target_chat.title}`...")
    
    added = 0
    for (member_id,) in members:
        try:
            await client.add_chat_members(target_chat.id, member_id)
            added += 1
            await asyncio.sleep(2)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except:
            pass
    
    await message.edit(f"✅ Added {added}/{len(members)} members!")

# ===================== AUTO FORWARD HANDLER =====================

@app.on_message(filters.channel | filters.group)
async def auto_forward(client, message):
    source_id = message.chat.id
    
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT p.dest_id, u.* FROM forward_pairs p
        JOIN users u ON p.user_id = u.user_id
        WHERE p.source_id = ? AND u.auto_forward = 1 AND u.is_blocked = 0
    """, (source_id,))
    
    forwards = cursor.fetchall()
    conn.close()
    
    for fwd in forwards:
        settings = dict(fwd)
        dest_id = settings['dest_id']
        user_id = settings['user_id']
        
        # Filter check
        if settings['filter_enabled']:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT word FROM filters WHERE user_id = ?", (user_id,))
            filters_list = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            text = (message.text or message.caption or "").lower()
            if any(word in text for word in filters_list):
                continue
        
        try:
            if settings['repost_mode']:
                # Advanced repost with header/footer
                caption = message.caption or message.text or ""
                
                if settings['link_remove']:
                    caption = remove_links(caption)
                
                if settings['replace_text']:
                    old, new = settings['replace_text'].split('|', 1)
                    caption = caption.replace(old, new)
                
                header = settings['header'] or ""
                footer = settings['footer'] or ""
                new_caption = f"{header}\n{caption}\n{footer}".strip()
                
                await message.copy(dest_id, caption=new_caption)
            else:
                await message.copy(dest_id)
            
            update_stat(user_id, 'messages_forwarded')
            await asyncio.sleep(0.1)
            
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except:
            pass

# ===================== QUICK SPAM COMMANDS =====================

@app.on_message(filters.command(["q", "qq", "qqq"], prefixes="/") & filters.me)
async def quick_spam(client, message):
    counts = {"q": 10, "qq": 50, "qqq": 100}
    count = counts[message.command[0]]
    
    if len(message.command) < 2:
        await message.edit(f"⚠️ Usage: `/{message.command[0]} <text>`")
        return
    
    text = message.text.split(None, 1)[1]
    
    for i in range(count):
        try:
            await message.reply(text)
            await asyncio.sleep(0.5)
        except FloodWait as e:
            await asyncio.sleep(e.value)

# ===================== ADVANCED SPAM FEATURES =====================

@app.on_message(filters.command("spam5", prefixes="/") & filters.me)
async def spam_5_templates(client, message):
    """Spam with 5 different message templates"""
    if len(message.command) < 2:
        await message.edit("⚠️ Usage: `/spam5 @target`")
        return
    
    target = extract_username(message.command[1])
    
    templates = [
        "🔥 Amazing Offer! Join Now!",
        "💰 Earn Money Fast - Limited Time!",
        "🎁 Free Gift for First 100 Members!",
        "⚡ Don't Miss This Opportunity!",
        "🌟 Best Deal of the Year!"
    ]
    
    try:
        target_chat = await client.get_chat(target)
        await message.edit(f"🎯 Starting 5-template spam...")
        
        for template in templates:
            for _ in range(10):
                await client.send_message(target_chat.id, template)
                await asyncio.sleep(2)
        
        await message.edit("✅ Spam completed!")
    except Exception as e:
        await message.edit(f"❌ Error: `{str(e)}`")

# ===================== STATISTICS =====================

@app.on_message(filters.command("stats", prefixes="/") & filters.me)
async def show_stats(client, message):
    user_id = message.from_user.id
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stats WHERE user_id = ?", (user_id,))
    stats = cursor.fetchone()
    conn.close()
    
    if not stats:
        await message.edit("📊 No statistics yet!")
        return
    
    text = f"""
📊 **YOUR STATISTICS**

📨 Messages Forwarded: {stats[1]}
💬 Messages Spammed: {stats[2]}
👥 Members Scraped: {stats[3]}
⚡ Reactions Sent: {stats[4]}

Status: {"🎁 Premium" if is_premium(user_id) else "🆓 Free"}
"""
    
    await message.edit(text)

# ===================== SETTINGS =====================

@app.on_message(filters.command("settings", prefixes="/") & filters.me)
async def show_settings(client, message):
    user_id = message.from_user.id
    settings = get_user_settings(user_id)
    
    text = f"""
⚙️ **YOUR SETTINGS**

Auto Forward: {"✅" if settings['auto_forward'] else "❌"}
Repost Mode: {"✅" if settings['repost_mode'] else "❌"}
Filter Enabled: {"✅" if settings['filter_enabled'] else "❌"}
Link Remove: {"✅" if settings['link_remove'] else "❌"}

Spam Count: {settings['spam_count']}
Spam Delay: {settings['spam_delay']}s
Random Mode: {"✅" if settings['random_mode'] else "❌"}

Header: {settings['header'] or 'None'}
Footer: {settings['footer'] or 'None'}
"""
    
    await message.edit(text)

@app.on_message(filters.command("toggle", prefixes="/") & filters.me)
async def toggle_setting(client, message):
    user_id = message.from_user.id
    
    if len(message.command) < 2:
        await message.edit("⚠️ Usage: `/toggle <auto|repost|filter|linkremove>`")
        return
    
    setting_map = {
        'auto': 'auto_forward',
        'repost': 'repost_mode',
        'filter': 'filter_enabled',
        'linkremove': 'link_remove'
    }
    
    key = message.command[1].lower()
    if key not in setting_map:
        await message.edit("❌ Invalid setting!")
        return
    
    db_key = setting_map[key]
    settings = get_user_settings(user_id)
    new_value = not settings[db_key]
    update_setting(user_id, db_key, int(new_value))
    
    await message.edit(f"✅ **{key.title()}** {'enabled' if new_value else 'disabled'}!")

# ===================== RUN THE BOT =====================

if __name__ == "__main__":
    print("🔥 Initializing Ultra Advanced Userbot...")
    init_db()
    print("✅ Database ready!")
    print("🚀 Starting userbot...")
    app.run()
    print("👋 Userbot stopped!")
