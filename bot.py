# bot_simple.py - упрощенная версия бота
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8236167537:AAHJ0RAVCzZb6idL2Avm3KGGpT6LY0il5Fk"
# Замените на ваш URL от Render
WEB_APP_URL = "https://your-app-name.onrender.com"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎮 Играть в Cosmic Miner", web_app={"url": WEB_APP_URL})]]
    
    await update.message.reply_text(
        "🚀 *Добро пожаловать в Cosmic Miner!*\n\n"
        "Нажми кнопку ниже чтобы начать играть!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == '__main__':
    main()