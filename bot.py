from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from openpyxl import load_workbook
import logging
import os
import requests

logging.basicConfig(level=logging.INFO)
token = os.getenv("TELEGRAM_BOT_TOKEN")
onedrive_url = os.getenv("ONEDRIVE_EXCEL_URL")

async def recibir_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        monto = float(update.message.text)

        # Descargar archivo de OneDrive
        response = requests.get(onedrive_url)
        with open('Tarjeta de Credito.xlsx', 'wb') as f:
            f.write(response.content)

        # Cargar workbook
        wb = load_workbook('Tarjeta de Credito.xlsx')
        ws = wb['21 de agosto']

        # Encontrar primera celda vacía en columna B desde B3
        fila = 3
        while ws[f'B{fila}'].value is not None:
            fila += 1

        # Agregar monto
        ws[f'B{fila}'].value = monto

        # Guardar
        wb.save('Tarjeta de Credito.xlsx')

        # Subir de vuelta a OneDrive
        with open('Tarjeta de Credito.xlsx', 'rb') as f:
            requests.put(onedrive_url, data=f)

        # Leer total de J2
        total = ws['J2'].value

        respuesta = f"✅ Agregado: ${monto} en fila B{fila}\n\n💰 Total de gastos: ${total}"
        await update.message.reply_text(respuesta)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Envíame un monto y lo agrego a tu tarjeta 💳")

if __name__ == '__main__':
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto))
    app.run_polling()