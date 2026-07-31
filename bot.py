import logging
import json
import urllib.parse
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# Configuration
BOT_TOKEN = "8564193233:AAGVFJG_IlC0_CImb06HzuBS-PnNaaACeDg"
BASE_WEB_APP_URL = "https://mikigode.github.io/Daily-sales/"

# Target Telegram Group ID
GROUP_CHAT_ID = -1005578584676  

# Sets for user permissions
APPROVED_USERS = set()
ADMIN_IDS = {393743768}

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Shows dynamic MiniApp button ONLY if the user is approved/admin.
    Passes the Telegram user's name dynamically to the Web App URL parameters.
    """
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name

    if user_id in APPROVED_USERS or user_id in ADMIN_IDS:
        # Dynamically append user name and user ID to the Web App URL
        encoded_name = urllib.parse.quote(user_name)
        dynamic_url = f"{BASE_WEB_APP_URL}?rep={encoded_name}&user_id={user_id}"

        web_app_btn = KeyboardButton(
            text="📊 Open Daily Sales Form", 
            web_app=WebAppInfo(url=dynamic_url)
        )
        reply_markup = ReplyKeyboardMarkup([[web_app_btn]], resize_keyboard=True)
        await update.message.reply_text(
            f"👋 Welcome back, {user_name}! Click below to submit your daily report.",
            reply_markup=reply_markup
        )
    else:
        keyboard = [[InlineKeyboardButton("📩 Request Access from Admin", callback_data=f"req_access:{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        restricted_msg = (
            "🔒 *Access Restricted*\n\n"
            "You are not an approved sales representative yet.\n"
            "Click the button below to request access from the group admins."
        )
        
        await update.message.reply_text(
            restricted_msg,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def handle_approval_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered when an unapproved user clicks 'Request Access from Admin'."""
    query = update.callback_query
    await query.answer()
    
    req_user = query.from_user
    req_user_id = req_user.id

    approve_keyboard = [
        [
            InlineKeyboardButton("✅ Approve Rep", callback_data=f"approve:{req_user_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject:{req_user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(approve_keyboard)

    group_msg = (
        f"🚨 *NEW ACCESS REQUEST*\n\n"
        f"👤 *Name:* {req_user.full_name}\n"
        f"🌐 *Username:* @{req_user.username if req_user.username else 'N/A'}\n"
        f"🆔 *User ID:* `{req_user_id}`\n\n"
        f"Group Admins: Click below to grant or deny access."
    )

    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=group_msg,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        await query.edit_message_text("✅ Your access request has been posted to the Group for Admin review.")
    except Exception as e:
        logging.error(f"Error sending message to group {GROUP_CHAT_ID}: {e}")
        await query.edit_message_text("⚠️ Could not reach group. Please ensure the bot is added to the group as an Admin.")

async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles Admin clicking 'Approve Rep' or 'Reject' inside the group chat."""
    query = update.callback_query
    await query.answer()
    
    clicker_id = update.effective_user.id
    action, target_id = query.data.split(":")
    target_id = int(target_id)

    is_admin = False
    if clicker_id in ADMIN_IDS:
        is_admin = True
    else:
        try:
            member = await context.bot.get_chat_member(chat_id=GROUP_CHAT_ID, user_id=clicker_id)
            if member.status in ["administrator", "creator"]:
                is_admin = True
        except Exception as e:
            logging.error(f"Error checking chat member status: {e}")

    if not is_admin:
        await query.answer("⚠️ Only Group Admins can approve or reject representatives!", show_alert=True)
        return

    admin_name = update.effective_user.full_name

    if action == "approve":
        APPROVED_USERS.add(target_id)
        
        await query.edit_message_text(
            f"✅ *Representative Approved!*\n\n👤 User ID `{target_id}` has been approved by {admin_name}.",
            parse_mode="Markdown"
        )
        
        try:
            web_app_btn = KeyboardButton(
                text="📊 Open Daily Sales Form", 
                web_app=WebAppInfo(url=f"{BASE_WEB_APP_URL}?user_id={target_id}")
            )
            reply_markup = ReplyKeyboardMarkup([[web_app_btn]], resize_keyboard=True)
            
            await context.bot.send_message(
                chat_id=target_id,
                text="🎉 *Access Granted!*\n\nYour account has been approved by the Admin. Click below to open your Daily Sales Form.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Error sending approval notification to user: {e}")

    elif action == "reject":
        await query.edit_message_text(
            f"❌ *Request Rejected*\n\nAccess request for user `{target_id}` was rejected by {admin_name}.",
            parse_mode="Markdown"
        )

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Group command allowing admins to approve directly: /approve"""
    clicker_id = update.effective_user.id
    
    is_admin = False
    if clicker_id in ADMIN_IDS:
        is_admin = True
    else:
        try:
            member = await context.bot.get_chat_member(chat_id=update.effective_chat.id, user_id=clicker_id)
            if member.status in ["administrator", "creator"]:
                is_admin = True
        except Exception as e:
            logging.error(f"Error checking chat member: {e}")

    if not is_admin:
        await update.message.reply_text("⚠️ Only Group Admins can use this command.")
        return

    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        target_name = update.message.reply_to_message.from_user.full_name
        APPROVED_USERS.add(target_id)
        await update.message.reply_text(f"✅ **{target_name}** (`{target_id}`) is now an approved Sales Representative!", parse_mode="Markdown")
        return

    if context.args:
        try:
            target_id = int(context.args[0])
            APPROVED_USERS.add(target_id)
            await update.message.reply_text(f"✅ User `{target_id}` is now approved!", parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ Invalid User ID provided.")
    else:
        await update.message.reply_text("Usage: Reply to a user's message with `/approve` or use `/approve <user_id>`.", parse_mode="Markdown")

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives data sent from the Mini App and posts the formatted report to the Group."""
    user_id = update.effective_user.id
    user_full_name = update.effective_user.full_name

    if user_id not in APPROVED_USERS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to submit reports.")
        return

    try:
        data = json.loads(update.message.web_app_data.data)
        
        # Dynamically determine the sales rep name
        rep_name = data.get('rep') or user_full_name
        
        # Extract and parse direct collections
        coop = float(data.get('coop', 0) or 0)
        telebirr = float(data.get('telebirr', 0) or 0)
        bemekina = float(data.get('bemekina', 0) or 0)
        
        # Extract and parse credit sales
        hotel = float(data.get('hotel', 0) or 0)
        credit_gebi = float(data.get('creditGebi', 0) or 0)
        
        total_collected = coop + telebirr + bemekina
        total_credit = hotel + credit_gebi
        
        report_text = (
            f"📋 **DAILY SALES & COLLECTION REPORT**\n"
            f"👤 **Sales Rep:** {rep_name}\n"
            f"📅 **Date:** {data.get('date', 'N/A')}\n"
            f"----------------------------------\n"
            f"📦 **PACKAGED SALES:**\n"
            f"• Gross Packs: `{data.get('grossPacks', 0):,}`\n"
            f"• Net Sold Packs: `{data.get('netSold', 0):,}`\n\n"
            f"💵 **DIRECT COLLECTIONS (CASH & BANK):**\n"
            f"• Coop Bank (የcoop ባንክ): `{coop:,.2f} ETB`\n"
            f"• Telebirr (ቴሌብር): `{telebirr:,.2f} ETB`\n"
            f"• Bemekina (በመኪና የተወሰደ): `{bemekina:,.2f} ETB`\n"
            f"💰 **Total Direct Collections:** `{total_collected:,.2f} ETB`\n\n"
            f"📝 **CREDIT SALES (RECEIVABLES):**\n"
            f"• Best West Hotel (ቤስት ዌስት): `{hotel:,.2f} ETB`\n"
            f"• Credit Gebi (መገናኛ ጁስ): `{credit_gebi:,.2f} ETB`\n"
            f"🏷️ **Total Credit Sales:** `{total_credit:,.2f} ETB`\n\n"
            f"📌 **RECONCILIATION & ADJUSTMENTS:**\n"
            f"• Target Sales (Total Birr): `{data.get('targetBirr', 0):,} ETB`\n"
            f"• Uncollected Funds (ያልገባ ብር): `{data.get('uncollected', 0):,} ETB`\n"
            f"• Yesterday's Balance (የትላንትና ቀሪ): `{data.get('yesterdayBalance', 0):,} ETB`\n\n"
            f"🏆 **GRAND TOTAL ACCOUNTED:** `{data.get('grandTotal', 0):,} ETB`"
        )
        
        await update.message.reply_text("✅ Report successfully submitted to the Group!", parse_mode="Markdown")

        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=report_text,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logging.error(f"Error processing WebApp data: {e}")
        await update.message.reply_text("❌ Error processing submitted report. Please try again.")

def main():
    """Start the Telegram bot."""
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve_command))
    app.add_handler(CallbackQueryHandler(handle_approval_request, pattern="^req_access:"))
    app.add_handler(CallbackQueryHandler(handle_admin_action, pattern="^(approve|reject):"))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    
    print("Bot is running with Dynamic Sales Rep & Credit Sales separation...")
    app.run_polling()

if __name__ == '__main__':
    main()
