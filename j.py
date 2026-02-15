import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler
)

# Bot configuration
BOT_TOKEN = "8591019608:AAFmwC7a7p50S572mqR1AbQsVibMzxAoPd4"
OWNER_CHAT_ID = 8211093641  # MUST be integer, not string!!!

# Conversation states
SELECTING_PAYMENT, WAITING_SCREENSHOT = range(2)

# Payment methods - Only Telebirr
PAYMENT_METHODS = {
    "telebirr": {
        "name": "Telebirr",
        "instructions": "💰 *Telebirr Payment Instructions*\n\n"
                        "Send **100 birr** using Telebirr.\n"
                        "Phone Number: **0946419482**\n"
                        "Name: **Birhane**\n\n"
                        "📸 After payment, click 'Send Screenshot' button below.",
        "account_info": "0946419482 - Birhane"
    }
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class PaymentBot:
    def __init__(self):
        self.user_payments = {}
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):

        # CONVERSATION HANDLER MUST BE ADDED FIRST
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.buy_callback, pattern="^buy_account$"),
                          CommandHandler("buy", self.buy_command)],
            states={
                SELECTING_PAYMENT: [
                    CallbackQueryHandler(self.select_payment_method,
                                         pattern="^telebirr$")
                ],
                WAITING_SCREENSHOT: [
                    MessageHandler(filters.PHOTO, self.receive_screenshot),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.ask_for_screenshot)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_payment)],
            allow_reentry=True
        )

        self.application.add_handler(conv_handler)

        # NORMAL COMMAND HANDLERS
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))

        # MAIN MENU CALLBACK HANDLER
        self.application.add_handler(CallbackQueryHandler(self.main_menu_handler))

        # GENERAL MESSAGE HANDLER
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.default_reply))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "🤖 **Welcome to JTR Backtester Premium Subscription!**\n\n"
            "💰 **100 birr for a lifetime access**\n\n"
            "Click 'Buy Account' to get started 👇"
        )

        keyboard = [
            [InlineKeyboardButton("🛒 Buy Account", callback_data="buy_account")]
        ]

        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    async def buy_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await self.buy_command(update, context)
        return SELECTING_PAYMENT

    async def buy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "💳 **Choose Payment Method**\n\n"
            "Select payment option below 👇"
        )

        keyboard = [
            [InlineKeyboardButton("📱 Telebirr", callback_data="telebirr")],
            [InlineKeyboardButton("⬅️ Back", callback_data="start")]
        ]

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

        return SELECTING_PAYMENT

    async def select_payment_method(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        method = query.data
        user_id = query.from_user.id

        self.user_payments[user_id] = {
            "method": method,
            "username": query.from_user.username,
            "user_id": user_id
        }

        info = PAYMENT_METHODS[method]

        text = (
            f"{info['instructions']}\n\n"
            f"📌 *Send to:* `{info['account_info']}`\n\n"
            "Click the button below after payment 👇"
        )

        keyboard = [
            [InlineKeyboardButton("📤 I Have Done Payment - Send Screenshot", callback_data="send_screenshot")],
            [InlineKeyboardButton("⬅️ Back", callback_data="buy_account")]
        ]

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

        return WAITING_SCREENSHOT

    async def receive_screenshot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id

        if user_id not in self.user_payments:
            await update.message.reply_text("❌ Please start again using /buy.")
            return ConversationHandler.END

        photo = update.message.photo[-1].file_id
        method = self.user_payments[user_id]["method"]
        pm = PAYMENT_METHODS[method]

        # Send confirmation to user
        await update.message.reply_text(
            "✅ *Screenshot received!*\n\n"
            "⏳ **Verification in progress...**\n"
            "Once approved, you will receive a username and password for JTR Backtester.",
            parse_mode="Markdown"
        )

        # Send to owner with user info
        caption = (
            f"🚨 **New Payment Received**\n\n"
            f"👤 User: @{user.username if user.username else 'No Username'}\n"
            f"🆔 User ID: `{user_id}`\n"
            f"💳 Method: {pm['name']}\n"
            f"📌 Account: `{pm['account_info']}`"
        )

        await context.bot.send_photo(
            chat_id=OWNER_CHAT_ID,
            photo=photo,
            caption=caption,
            parse_mode="Markdown"
        )

        # Clean up
        del self.user_payments[user_id]

        return ConversationHandler.END

    async def ask_for_screenshot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📸 Please send the payment screenshot.")
        return WAITING_SCREENSHOT

    async def cancel_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id in self.user_payments:
            del self.user_payments[user_id]

        await update.message.reply_text("❌ Payment cancelled.")
        return ConversationHandler.END

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "📘 **How to Purchase**\n\n"
            "1️⃣ Press *Buy Account*\n"
            "2️⃣ Choose Telebirr payment\n"
            "3️⃣ Send 100 birr to 0946419482 (Birhane)\n"
            "4️⃣ Send screenshot after payment\n"
            "5️⃣ Wait for verification\n"
            "6️⃣ Receive your account details"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def main_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data

        if data == "send_screenshot":
            await query.answer()
            await query.edit_message_text("📸 **Now send your payment screenshot.**\n\nJust take a photo and send it here.")
            return WAITING_SCREENSHOT

        elif data == "start":
            await query.answer()
            await self.start_command(update, context)

        elif data == "buy_account":
            await query.answer()
            await self.buy_command(update, context)
            return SELECTING_PAYMENT

    async def default_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Use /start to begin or /buy to purchase JTR Backtester.")

    def run(self):
        print("🤖 JTR Backtester Bot is running...")
        self.application.run_polling()


if __name__ == "__main__":
    PaymentBot().run()
