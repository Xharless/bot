from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openpyxl import Workbook, load_workbook
from pathlib import Path
import logging
import os

logging.basicConfig(level=logging.INFO)
token = os.getenv("TELEGRAM_BOT_TOKEN")

async def recibir_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        monto = float(update.message.text)

        archivo = 'montos.xlsx'
        if not Path(archivo).exists():
            wb = Workbook()
            ws = wb.active
            ws['A1'] = 'Monto'
        else:
            wb = load_workbook(archivo)

        ws = wb.active
        ws.append([monto])
        wb.save(archivo)

        montos = []
        for row in ws.iter_rows(min_row=2, max_col=1, values_only=True):
            if row[0] and isinstance(row[0], (int, float)):
                montos.append(row[0])

        total = sum(montos)
        lista_montos = ', '.join([f"${m}" for m in montos])

        respuesta = f"✅ Agregado: ${monto}\n\n📊 Todos: {lista_montos}\n💰 Total: ${total}"
        await update.message.reply_text(respuesta)
    except ValueError:
        await update.message.reply_text("❌ Envía solo un número\nEj: 50000")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Envíame un monto y lo agrego 💰")

if __name__ == '__main__':
    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto))
    app.run_polling()