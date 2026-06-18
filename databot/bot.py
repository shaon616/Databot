#!/usr/bin/env python3
"""
DataShop Telegram Bot
- Refer code required for registration
- Buy refer code from bot if you don't have one ($350)
- 1K Data = $90 (Crypto payment)
"""

import os
import json
import random
import string
import logging
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Config ─────────────────────────────────────────────────────────────────
BOT_TOKEN   = "8948062827:AAHEfes-kBhDMPnHcsjTzcjDOuV-eWE6pOI"   # Get from @BotFather
ADMIN_IDS   = [6730437277]             # Your Telegram User ID

# Crypto Wallet Addresses
CRYPTO_WALLETS = {
    "USDT (TRC20)": "TLw6aY39ic93PgJchZjtgmB57HBxu8dPoc",
    "USDT (ERC20)": "0x899e9906d5dd1302f31e5c416dc1c18ef948e957",
    "BTC":          "13b63ji7MV8NnMyNrLEjfizAhrShNGfvxX",
}

# Pricing
DATA_PRICE_USD   = 90   # Price for 1K Data
REFER_CODE_PRICE = 350    # Price to buy a refer code
DATA_UNIT_LABEL  = "1K Data"

# Conversation states
(
    STATE_ENTER_REFER,
    STATE_BUY_REFER_PAYMENT,
    STATE_SELECT_DATA_PACKAGE,
    STATE_SELECT_CRYPTO,
    STATE_SUBMIT_TXID,
    STATE_ADMIN_BROADCAST,
) = range(6)

# ─── Database (JSON file — use SQLite/MongoDB in production) ─────────────────
DB_FILE = "database.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {
        "users": {},
        "refer_codes": {},
        "orders": {},
        "pending_payments": {}
    }

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def generate_refer_code(length=8):
    return "REF-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_order_id():
    return "ORD-" + "".join(random.choices(string.digits, k=8))

# ─── /start ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_db()

    if user_id in db["users"] and db["users"][user_id].get("registered"):
        await show_main_menu(update, context)
        return ConversationHandler.END

    kb = [
        [InlineKeyboardButton("✅ I Have a Refer Code", callback_data="has_refer")],
        [InlineKeyboardButton("🛒 Buy Refer Code ($350)", callback_data="buy_refer")],
    ]
    await update.message.reply_text(
        "🌐 *Welcome to DataShop Bot!*\n\n"
        "A *Refer Code* is required to create an account.\n\n"
        "Choose an option below 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return STATE_ENTER_REFER

# ─── Has Refer Code ───────────────────────────────────────────────────────────
async def has_refer_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔑 Please type your *Refer Code*:\n\n"
        "_Example: REF-ABC12345_",
        parse_mode="Markdown"
    )
    return STATE_ENTER_REFER

async def process_refer_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    code      = update.message.text.strip().upper()
    db        = load_db()

    if code not in db["refer_codes"]:
        await update.message.reply_text(
            "❌ *Invalid Refer Code!*\n\n"
            "This code does not exist. Please try again or buy a code.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
               [InlineKeyboardButton("🛒 Buy Refer Code ($350)", callback_data="buy_refer")]
            ])
        )
        return STATE_ENTER_REFER

    refer_code_data = db["refer_codes"][code]
    if refer_code_data.get("used"):
        await update.message.reply_text(
            "⚠️ This Refer Code has already been used!\n"
            "Please use a different code.",
            parse_mode="Markdown"
        )
        return STATE_ENTER_REFER

    # Register user
    db["users"][user_id] = {
        "name":        user_name,
        "user_id":     user_id,
        "refer_code":  code,
        "referred_by": refer_code_data.get("owner"),
        "registered":  True,
        "balance":     0,
        "joined_at":   datetime.now().isoformat()
    }

    # Mark code as used
    db["refer_codes"][code]["used"]    = True
    db["refer_codes"][code]["used_by"] = user_id
    save_db(db)

    # Notify referrer
    referrer_id = refer_code_data.get("owner")
    if referrer_id and referrer_id != "ADMIN":
        try:
            await context.bot.send_message(
                chat_id=int(referrer_id),
                text=f"🎉 *{user_name}* just joined using your Refer Code!",
                parse_mode="Markdown"
            )
        except:
            pass

    await update.message.reply_text(
        f"✅ *Registration Successful!*\n\n"
        f"Welcome {user_name}! Your account has been created.",
        parse_mode="Markdown"
    )
    await show_main_menu(update, context)
    return ConversationHandler.END

# ─── Buy Refer Code ───────────────────────────────────────────────────────────
async def buy_refer_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    wallets_text = "\n".join(
        [f"• *{name}:*\n`{addr}`" for name, addr in CRYPTO_WALLETS.items()]
    )

    await query.edit_message_text(
        f"🛒 *Refer Code Purchase*\n\n"
        f"💵 Price: *${REFER_CODE_PRICE} USDT*\n\n"
        f"Send payment to any wallet below:\n\n"
        f"{wallets_text}\n\n"
        f"After payment, send your *Transaction ID (TXID)*.\n"
        f"Admin will verify and send your code.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Submit TXID", callback_data="submit_refer_txid")]
        ])
    )
    context.user_data["payment_purpose"] = "refer_code"
    return STATE_BUY_REFER_PAYMENT

async def submit_refer_txid_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📤 Please type or paste your *Transaction ID (TXID)*:",
        parse_mode="Markdown"
    )
    return STATE_BUY_REFER_PAYMENT

async def receive_refer_txid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    txid      = update.message.text.strip()
    db        = load_db()

    order_id = generate_order_id()
    db["pending_payments"][order_id] = {
        "type":      "refer_code_purchase",
        "user_id":   user_id,
        "user_name": user_name,
        "txid":      txid,
        "amount":    REFER_CODE_PRICE,
        "status":    "pending",
        "created":   datetime.now().isoformat()
    }
    save_db(db)

    # Notify admins
    for admin_id in ADMIN_IDS:
        try:
            kb = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_refer_{order_id}"),
                    InlineKeyboardButton("❌ Reject",  callback_data=f"reject_{order_id}")
                ]
            ]
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🔔 *New Refer Code Order*\n\n"
                    f"👤 User: {user_name} (`{user_id}`)\n"
                    f"💵 Amount: ${REFER_CODE_PRICE}\n"
                    f"🆔 Order ID: `{order_id}`\n"
                    f"📋 TXID: `{txid}`"
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(kb)
            )
        except Exception as e:
            logger.error(f"Admin notify error: {e}")

    await update.message.reply_text(
        "⏳ *Payment Submitted!*\n\n"
        f"🆔 Order ID: `{order_id}`\n\n"
        "Admin will verify and send your Refer Code.\n"
        "This usually takes 1-2 hours.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ─── Main Menu ────────────────────────────────────────────────────────────────
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db      = load_db()
    user    = db["users"].get(user_id, {})

    kb = [
        ["🛒 Buy Data"],
        ["👤 My Profile", "📜 My Orders"],
        ["🔗 Share Refer Code"],
    ]
    if user_id in [str(a) for a in ADMIN_IDS]:
        kb.append(["⚙️ Admin Panel"])

    text = (
        f"👋 Welcome back, *{user.get('name', 'User')}!*\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"💾 {DATA_UNIT_LABEL} Price: *${DATA_PRICE_USD}*\n"
        f"💳 Payment: *Crypto (USDT / BTC)*\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"Choose an option from the menu below 👇"
    )

    msg = update.message if update.message else update.callback_query.message
    await msg.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

# ─── Buy Data ─────────────────────────────────────────────────────────────────
async def buy_data_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db      = load_db()

    if user_id not in db["users"] or not db["users"][user_id].get("registered"):
        await update.message.reply_text("⛔ You must register first! Send /start")
        return ConversationHandler.END

    packages = [
        ("1K Data",  90),
        ("5K Data",  300),
        ("10K Data", 700),
    ]

    kb = [
        [InlineKeyboardButton(f"📦 {label} — ${price}", callback_data=f"pkg_{label}_{price}")]
        for label, price in packages
    ]
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])

    await update.message.reply_text(
        "🛒 *Select a Data Package:*\n\n"
        "All prices are in USDT / BTC.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return STATE_SELECT_DATA_PACKAGE

async def select_package(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, label, price = query.data.split("_", 2)
    context.user_data["package_label"] = label
    context.user_data["package_price"] = int(price)

    kb = [
        [InlineKeyboardButton(name, callback_data=f"crypto_{name}")]
        for name in CRYPTO_WALLETS
    ]
    await query.edit_message_text(
        f"✅ Package: *{label}* — *${price}*\n\n"
        "💳 Select your payment method:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return STATE_SELECT_CRYPTO

async def select_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    crypto_name = query.data.replace("crypto_", "")
    wallet_addr = CRYPTO_WALLETS[crypto_name]
    context.user_data["crypto"] = crypto_name

    label = context.user_data["package_label"]
    price = context.user_data["package_price"]

    await query.edit_message_text(
        f"💳 *Payment Details*\n\n"
        f"📦 Package: *{label}*\n"
        f"💵 Amount: *${price} ({crypto_name})*\n\n"
        f"👛 Wallet Address:\n`{wallet_addr}`\n\n"
        f"⚠️ *Send the exact amount to this address.*\n\n"
        f"After sending, click the button below 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Submit TXID", callback_data="submit_data_txid")]
        ])
    )
    return STATE_SUBMIT_TXID

async def submit_data_txid_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📤 Please paste your *Transaction ID (TXID)*:\n\n"
        "_Copy it from your blockchain explorer_",
        parse_mode="Markdown"
    )
    return STATE_SUBMIT_TXID

async def receive_data_txid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    txid      = update.message.text.strip()
    db        = load_db()

    label  = context.user_data.get("package_label", "1K Data")
    price  = context.user_data.get("package_price", DATA_PRICE_USD)
    crypto = context.user_data.get("crypto", "USDT (TRC20)")

    order_id = generate_order_id()
    db["pending_payments"][order_id] = {
        "type":      "data_purchase",
        "user_id":   user_id,
        "user_name": user_name,
        "package":   label,
        "crypto":    crypto,
        "txid":      txid,
        "amount":    price,
        "status":    "pending",
        "created":   datetime.now().isoformat()
    }
    save_db(db)

    for admin_id in ADMIN_IDS:
        try:
            kb = [
                [
                    InlineKeyboardButton("✅ Approve & Deliver", callback_data=f"approve_data_{order_id}"),
                    InlineKeyboardButton("❌ Reject",            callback_data=f"reject_{order_id}")
                ]
            ]
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🔔 *New Data Order*\n\n"
                    f"👤 User: {user_name} (`{user_id}`)\n"
                    f"📦 Package: {label}\n"
                    f"💳 Crypto: {crypto}\n"
                    f"💵 Amount: ${price}\n"
                    f"🆔 Order ID: `{order_id}`\n"
                    f"📋 TXID: `{txid}`"
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(kb)
            )
        except Exception as e:
            logger.error(f"Admin notify error: {e}")

    await update.message.reply_text(
        "⏳ *Order Submitted!*\n\n"
        f"🆔 Order ID: `{order_id}`\n"
        f"📦 Package: {label}\n"
        f"💵 Amount: ${price}\n\n"
        "Admin will verify and deliver your data.\n"
        "This usually takes 1-2 hours.\n\n"
        "If you have any issues, contact support with your Order ID.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ─── Profile ──────────────────────────────────────────────────────────────────
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db      = load_db()
    user    = db["users"].get(user_id)

    if not user:
        await update.message.reply_text("❌ You are not registered. Send /start")
        return

    orders_count = sum(
        1 for o in db.get("orders", {}).values()
        if o.get("user_id") == user_id
    )

    my_code = next(
        (code for code, data in db["refer_codes"].items()
         if data.get("owner") == user_id),
        None
    )

    await update.message.reply_text(
        f"👤 *My Profile*\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"📛 Name: {user.get('name')}\n"
        f"📅 Joined: {user.get('joined_at', 'N/A')[:10]}\n"
        f"📦 Total Orders: {orders_count}\n"
        f"🔗 My Refer Code: `{my_code or 'None'}`\n",
        parse_mode="Markdown"
    )

# ─── Orders ───────────────────────────────────────────────────────────────────
async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db      = load_db()

    my_orders = [
        (oid, o) for oid, o in db.get("orders", {}).items()
        if o.get("user_id") == user_id
    ]

    if not my_orders:
        await update.message.reply_text(
            "📜 You have no orders yet.\n"
            "🛒 Buy some data!",
            parse_mode="Markdown"
        )
        return

    text = "📜 *My Orders:*\n\n"
    for oid, o in my_orders[-5:]:
        status_emoji = "✅" if o["status"] == "delivered" else "⏳"
        text += (
            f"{status_emoji} `{oid}`\n"
            f"   📦 {o.get('package')} | 💵 ${o.get('amount')}\n"
            f"   📅 {o.get('created', '')[:10]}\n\n"
        )
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── Share Refer Code ─────────────────────────────────────────────────────────
async def share_refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db      = load_db()

    my_code = next(
        (code for code, data in db["refer_codes"].items()
         if data.get("owner") == user_id),
        None
    )

    if not my_code:
        await update.message.reply_text(
            "❌ You do not have a Refer Code yet.\n\n"
            "A Refer Code is assigned after your first data purchase.\n"
            "Contact Admin for more info.",
            parse_mode="Markdown"
        )
        return

    bot_username = (await context.bot.get_me()).username
    await update.message.reply_text(
        f"🔗 *Your Refer Code:*\n\n"
        f"`{my_code}`\n\n"
        f"📲 Share this link:\n"
        f"https://t.me/{bot_username}?start={my_code}\n\n"
        f"Friends who register with your code will be linked to your account!",
        parse_mode="Markdown"
    )

# ─── Admin Panel ──────────────────────────────────────────────────────────────
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if int(user_id) not in ADMIN_IDS:
        await update.message.reply_text("⛔ Access denied. Admins only.")
        return

    db = load_db()
    total_users  = len(db["users"])
    total_orders = len(db.get("orders", {}))
    pending      = sum(1 for o in db["pending_payments"].values() if o["status"] == "pending")

    kb = [
        [InlineKeyboardButton("📊 Stats",             callback_data="admin_stats")],
        [InlineKeyboardButton("🔑 Generate Refer Code", callback_data="admin_gen_refer")],
        [InlineKeyboardButton("📢 Broadcast",          callback_data="admin_broadcast")],
    ]
    await update.message.reply_text(
        f"⚙️ *Admin Panel*\n\n"
        f"👥 Total Users: *{total_users}*\n"
        f"📦 Total Orders: *{total_orders}*\n"
        f"⏳ Pending Payments: *{pending}*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def admin_gen_refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    db   = load_db()
    code = generate_refer_code()
    db["refer_codes"][code] = {
        "owner":      "ADMIN",
        "used":       False,
        "created_at": datetime.now().isoformat()
    }
    save_db(db)

    await query.edit_message_text(
        f"✅ New Refer Code generated:\n\n"
        f"`{code}`\n\n"
        f"You can share this with anyone.",
        parse_mode="Markdown"
    )



# ─── Admin Broadcast ─────────────────────────────────────────────────────────
async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if user_id not in ADMIN_IDS:
        await query.answer("Access denied!", show_alert=True)
        return ConversationHandler.END

    await query.message.reply_text(
        "📢 Send the message you want to broadcast to all users:"
    )

    return STATE_ADMIN_BROADCAST

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    db = load_db()

    success = 0
    failed = 0

    for uid in db["users"].keys():
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=text
            )
            success += 1
        except Exception as e:
            logger.error(f"Broadcast error {uid}: {e}")
            failed += 1

    await update.message.reply_text(
        f"✅ Broadcast completed!\\n\\n"
        f"✔️ Sent: {success}\\n"
        f"❌ Failed: {failed}"
    )

    return ConversationHandler.END

# ─── Admin Approve / Reject ───────────────────────────────────────────────────
async def admin_approve_refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    order_id = query.data.replace("approve_refer_", "")
    db       = load_db()

    if order_id not in db["pending_payments"]:
        await query.answer("Order not found!")
        return

    payment = db["pending_payments"][order_id]
    user_id = payment["user_id"]

    code = generate_refer_code()
    db["refer_codes"][code] = {
        "owner":      "ADMIN",
        "used":       False,
        "created_at": datetime.now().isoformat()
    }
    db["pending_payments"][order_id]["status"] = "approved"
    save_db(db)

    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=(
                f"✅ *Your Payment Has Been Approved!*\n\n"
                f"🔑 Your Refer Code:\n`{code}`\n\n"
                f"Use this code to register. Send /start to begin."
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Send refer code error: {e}")

    await query.edit_message_text(
        f"✅ Approved! Refer Code `{code}` sent to user.",
        parse_mode="Markdown"
    )
    await query.answer("Approved!")

async def admin_approve_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    order_id = query.data.replace("approve_data_", "")
    db       = load_db()

    if order_id not in db["pending_payments"]:
        await query.answer("Order not found!")
        return

    payment = db["pending_payments"][order_id]
    user_id = payment["user_id"]

    db["orders"][order_id] = {**payment, "status": "delivered", "delivered_at": datetime.now().isoformat()}
    db["pending_payments"][order_id]["status"] = "approved"

    # Give user a refer code if they don't have one
    has_code = any(d.get("owner") == user_id for d in db["refer_codes"].values())
    new_refer = None
    if not has_code:
        new_refer = generate_refer_code()
        db["refer_codes"][new_refer] = {
            "owner":      user_id,
            "used":       False,
            "created_at": datetime.now().isoformat()
        }

    save_db(db)

    msg = (
        f"✅ *Payment Approved!*\n\n"
        f"📦 Package: *{payment.get('package')}* will be delivered shortly.\n"
        f"🆔 Order ID: `{order_id}`\n\n"
        "_Admin will contact you to deliver the data._"
    )
    if new_refer:
        msg += f"\n\n🔑 Your Refer Code: `{new_refer}`\nShare it with friends!"

    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=msg,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Delivery notify error: {e}")

    await query.edit_message_text(f"✅ Order `{order_id}` approved and user notified!", parse_mode="Markdown")
    await query.answer("Approved!")

async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    order_id = query.data.replace("reject_", "")
    db       = load_db()

    if order_id not in db["pending_payments"]:
        await query.answer("Order not found!")
        return

    user_id = db["pending_payments"][order_id]["user_id"]
    db["pending_payments"][order_id]["status"] = "rejected"
    save_db(db)

    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=(
                f"❌ *Payment Rejected*\n\n"
                f"🆔 Order ID: `{order_id}`\n\n"
                "Your TXID could not be verified.\n"
                "Please try again with a valid TXID or contact support."
            ),
            parse_mode="Markdown"
        )
    except:
        pass

    await query.edit_message_text(f"❌ Order `{order_id}` rejected!", parse_mode="Markdown")
    await query.answer("Rejected!")

# ─── Message Router ───────────────────────────────────────────────────────────
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🛒 Buy Data":
        return await buy_data_menu(update, context)
    elif text == "👤 My Profile":
        await show_profile(update, context)
    elif text == "📜 My Orders":
        await show_orders(update, context)
    elif text == "🔗 Share Refer Code":
        await share_refer(update, context)
    elif text == "⚙️ Admin Panel":
        await admin_panel(update, context)
    else:
        await update.message.reply_text("❓ Please select an option from the menu or send /start")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Registration conversation
    reg_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            STATE_ENTER_REFER: [
                CallbackQueryHandler(has_refer_code, pattern="^has_refer$"),
                CallbackQueryHandler(buy_refer_code, pattern="^buy_refer$"),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    process_refer_code
                ),
            ],
            STATE_BUY_REFER_PAYMENT: [
                CallbackQueryHandler(
                    submit_refer_txid_prompt,
                    pattern="^submit_refer_txid$"
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_refer_txid
                ),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Data purchase conversation
    data_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex("^🛒 Buy Data$"),
                buy_data_menu
            )
        ],
        states={
            STATE_SELECT_DATA_PACKAGE: [
                CallbackQueryHandler(
                    select_package,
                    pattern="^pkg_"
                ),
            ],
            STATE_SELECT_CRYPTO: [
                CallbackQueryHandler(
                    select_crypto,
                    pattern="^crypto_"
                ),
            ],
            STATE_SUBMIT_TXID: [
                CallbackQueryHandler(
                    submit_data_txid_prompt,
                    pattern="^submit_data_txid$"
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_data_txid
                ),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Broadcast conversation
    broadcast_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                admin_broadcast,
                pattern="^admin_broadcast$"
            )
        ],
        states={
            STATE_ADMIN_BROADCAST: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    send_broadcast
                )
            ]
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(reg_handler)
    app.add_handler(data_handler)
    app.add_handler(broadcast_handler)

    # Admin callbacks
    app.add_handler(
        CallbackQueryHandler(
            admin_gen_refer,
            pattern="^admin_gen_refer$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_approve_refer,
            pattern="^approve_refer_"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_approve_data,
            pattern="^approve_data_"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_reject,
            pattern="^reject_"
        )
    )

    # General messages
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router
        )
    )

    print("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
