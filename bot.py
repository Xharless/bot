from telegram import Update, ReplyKeyboardMarkup
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

BTN_TOTAL = "💰 Total"
BTN_GASTOS = "📊 Gastos"
BTN_PRODUCTOS = "🛒 Productos en cuotas"

MENU = ReplyKeyboardMarkup(
    [[BTN_TOTAL, BTN_GASTOS], [BTN_PRODUCTOS]],
    resize_keyboard=True,
)


def get_sheet():
    sh = gc.open_by_key(SHEET_ID)
    return sh.worksheet("21 de agosto")


async def ver_total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ws = get_sheet()
        total = ws.acell('J2').value
        await update.message.reply_text(f"💰 Total de gastos: {total}", reply_markup=MENU)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", reply_markup=MENU)


async def ver_gastos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ws = get_sheet()
        columna_b = ws.col_values(2)[2:]  # Desde B3
        montos = [v for v in columna_b if v]
        total = ws.acell('J2').value

        lista = '\n'.join([f"• {g}" for g in montos])
        await update.message.reply_text(f"📊 Gastos:\n{lista}\n\n💰 Total: {total}", reply_markup=MENU)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", reply_markup=MENU)


async def ver_productos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ws = get_sheet()
        filas = ws.get('D7:I200')

        productos = []
        for fila in filas:
            if not fila or not fila[0]:
                continue
            producto = fila[0]
            costo = fila[2] if len(fila) > 2 else ""
            cuota = fila[4] if len(fila) > 4 else ""
            valor_cuota = fila[5] if len(fila) > 5 else ""
            productos.append(
                f"🛒 {producto}\n   Costo: {costo} | Cuota: {cuota} | Valor cuota: {valor_cuota}"
            )

        if not productos:
            await update.message.reply_text("No hay productos en cuotas registrados.", reply_markup=MENU)
            return

        texto = '\n\n'.join(productos)
        await update.message.reply_text(f"📦 Productos en cuotas:\n\n{texto}", reply_markup=MENU)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", reply_markup=MENU)


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
        await update.message.reply_text(f"✅ Agregado: {monto}\n\n💰 Total: {total}", reply_markup=MENU)
    except ValueError:
        await update.message.reply_text("❌ Envía solo un número o usa los botones del menú", reply_markup=MENU)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", reply_markup=MENU)


async def post_init(application: Application):
    # Sin comandos en el menú de Telegram: solo botones en el chat
    await application.bot.set_my_commands([])


if __name__ == '__main__':
    app = Application.builder().token(token).post_init(post_init).build()
    app.add_handler(CommandHandler("total", ver_total))
    app.add_handler(CommandHandler("gastos", ver_gastos))
    app.add_handler(CommandHandler("productos", ver_productos))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_TOTAL}$"), ver_total))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_GASTOS}$"), ver_gastos))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_PRODUCTOS}$"), ver_productos))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=token,
        webhook_url=f"{RENDER_URL}/{token}"
    )
