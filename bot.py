from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from openpyxl import load_workbook
import logging
import os
import requests

logging.basicConfig(level=logging.INFO)
token = os.getenv("TELEGRAM_BOT_TOKEN")
onedrive_url = os.getenv("ONEDRIVE_EXCEL_URL")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comandos disponibles:\n"
        "/total - Ver total de gastos\n"
        "/gastos - Ver todos los gastos\n"
        "\nO simplemente envía un número para agregar un gasto"
    )

async def ver_total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(onedrive_url)
        with open('Tarjeta de Credito.xlsx', 'wb') as f:
            f.write(response.content)

        wb = load_workbook('Tarjeta de Credito.xlsx')
        ws = wb['21 de agosto']
        total = ws['J2'].value

        await update.message.reply_text(f"💰 Total de gastos: ${total}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def ver_gastos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(onedrive_url)
        with open('Tarjeta de Credito.xlsx', 'wb') as f:
            f.write(response.content)

        wb = load_workbook('Tarjeta de Credito.xlsx')
        ws = wb['21 de agosto']

        gastos = []
        fila = 3
        while ws[f'B{fila}'].value is not None:
            gastos.append(ws[f'B{fila}'].value)
            fila += 1

        total = ws['J2'].value
        lista = '\n'.join([f"• ${g}" for g in gastos])

        await update.message.reply_text(f"📊 Gastos:\n{lista}\n\n💰 Total: ${total}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def recibir_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        monto = float(update.message.text)

        response = requests.get(onedrive_url)
        with open('Tarjeta de Credito.xlsx', 'wb') as f:
            f.write(response.content)

        wb = load_workbook('Tarjeta de Credito.xlsx')
        ws = wb['21 de agosto']

        fila = 3
        while ws[f'B{fila}'].value is not None:
            fila += 1

        ws[f'B{fila}'].value = monto
        wb.save('Tarjeta de Credito.xlsx')

        with open('Tarjeta de Credito.xlsx', 'rb') as f:
            requests.put(onedrive_url, data=f)

        total = ws['J2'].value

        await update.message.reply_text(f"✅ Agregado: ${monto}\n\n💰 Total: ${total}")
    except ValueError:
        await update.message.reply_text("❌ Envía solo un número")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("total", ver_total))
    app.add_handler(CommandHandler("gastos", ver_gastos))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto))
    app.run_polling()