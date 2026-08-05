from telegram import Update, BotCommand
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
import gspread
from google.oauth2.service_account import Credentials
import logging
import os
import json

logging.basicConfig(level=logging.INFO)
token = os.getenv("TELEGRAM_BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", "10000"))
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds_json = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
gc = gspread.authorize(creds)

def get_sheet():
    sh = gc.open_by_key(SHEET_ID)
    return sh.worksheet("21 de agosto")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comandos disponibles:\n"
        "/total - Ver total de gastos\n"
        "/gastos - Ver todos los gastos\n"
        "\nO simplemente envía un número para agregar un gasto"
    )

async def ver_total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ws = get_sheet()
        total = ws.acell('J2').value
        await update.message.reply_text(f"💰 Total de gastos: ${total}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def ver_gastos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ws = get_sheet()
        columna_b = ws.col_values(2)[2:]  # Desde B3
        montos = [v for v in columna_b if v]
        total = ws.acell('J2').value

        lista = '\n'.join([f"• ${g}" for g in montos])
        await update.message.reply_text(f"📊 Gastos:\n{lista}\n\n💰 Total: {total}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def recibir_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        monto = float(update.message.text)
        ws = get_sheet()

        columna_b = ws.col_values(2)
        fila = len(columna_b) + 1
        if fila < 3:
            fila = 3

        ws.update_cell(fila, 2, monto)

        total = ws.acell('J2').value
        await update.message.reply_text(f"✅ Agregado: ${monto}\n\n💰 Total: {total}")
    except ValueError:
        await update.message.reply_text("❌ Envía solo un número")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start", "Ver ayuda"),
        BotCommand("total", "Ver total de gastos"),
        BotCommand("gastos", "Ver todos los gastos"),
    ])

if __name__ == '__main__':
    app = Application.builder().token(token).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("total", ver_total))
    app.add_handler(CommandHandler("gastos", ver_gastos))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=token,
        webhook_url=f"{RENDER_URL}/{token}"
    )