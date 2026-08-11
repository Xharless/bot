from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
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
BTN_AGREGAR_CUOTA = "➕ Agregar cuota"

MENU = ReplyKeyboardMarkup(
    [[BTN_TOTAL, BTN_GASTOS], [BTN_PRODUCTOS, BTN_AGREGAR_CUOTA]],
    resize_keyboard=True,
)

PRODUCTO, COSTO, CUOTAS = range(3)


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


async def agregar_cuota_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Vamos a agregar un producto en cuotas.\n¿Cuál es el nombre del producto?\n\n"
        "(envía /cancelar en cualquier momento para salir)"
    )
    return PRODUCTO


async def recibir_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['producto'] = update.message.text
    await update.message.reply_text("¿Cuál es el costo total del producto?")
    return COSTO


async def recibir_costo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        costo = float(update.message.text.replace(',', '.'))
    except ValueError:
        await update.message.reply_text("❌ Envía solo un número para el costo")
        return COSTO

    context.user_data['costo'] = costo
    await update.message.reply_text("¿En cuántas cuotas?")
    return CUOTAS


async def recibir_cuotas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cuotas = int(update.message.text)
        if cuotas <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Envía un número entero de cuotas")
        return CUOTAS

    producto = context.user_data['producto']
    costo = context.user_data['costo']
    valor_cuota = round(costo / cuotas, 2)

    try:
        ws = get_sheet()

        # Próxima fila libre de la tabla de cuotas (desde la fila 7)
        columna_d = ws.col_values(4)
        fila = len(columna_d) + 1
        if fila < 7:
            fila = 7

        ws.update_cell(fila, 4, producto)    # D
        ws.update_cell(fila, 6, costo)       # F
        ws.update_cell(fila, 8, cuotas)       # H
        ws.update_cell(fila, 9, valor_cuota)  # I
        ws.merge_cells(f'D{fila}:E{fila}')
        ws.merge_cells(f'F{fila}:G{fila}')

        # El valor de la cuota se agrega también como gasto
        columna_b = ws.col_values(2)
        fila_gasto = len(columna_b) + 1
        if fila_gasto < 3:
            fila_gasto = 3
        ws.update_cell(fila_gasto, 2, valor_cuota)

        total = ws.acell('J2').value
        await update.message.reply_text(
            f"✅ Producto agregado a cuotas: {producto}\n"
            f"Costo: {costo} | Cuotas: {cuotas} | Valor cuota: {valor_cuota}\n\n"
            f"💰 Se agregó {valor_cuota} a gastos. Total: {total}",
            reply_markup=MENU,
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", reply_markup=MENU)

    context.user_data.clear()
    return ConversationHandler.END


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Operación cancelada.", reply_markup=MENU)
    return ConversationHandler.END


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

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{BTN_AGREGAR_CUOTA}$"), agregar_cuota_start)],
        states={
            PRODUCTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_producto)],
            COSTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_costo)],
            CUOTAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_cuotas)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    app.add_handler(conv_handler)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=token,
        webhook_url=f"{RENDER_URL}/{token}"
    )
