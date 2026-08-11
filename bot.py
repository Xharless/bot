from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
import gspread
from google.oauth2.service_account import Credentials
import logging
import os
import json
import html

PARSE_MODE = "HTML"

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
BTN_HOJA_MENU = "📑 Hojas"
BTN_ELEGIR_HOJA = "📋 Elegir hoja"
BTN_NUEVA_HOJA = "🗂️ Nueva hoja mensual"
BTN_ELIMINAR_HOJA = "🗑️ Eliminar hoja"

CB_TOTAL = "total"
CB_GASTOS = "gastos"
CB_PRODUCTOS = "productos"
CB_AGREGAR_CUOTA = "agregar_cuota"
CB_HOJA_MENU = "hoja_menu"
CB_HOJAS = "hojas"
CB_NUEVA_HOJA = "nueva_hoja"
CB_ELIMINAR_HOJA = "eliminar_hoja"
CB_CANCELAR = "cancelar"
CB_HOJA_PREFIX = "hoja:"
CB_DELHOJA_PREFIX = "delhoja:"
CB_CONFIRMDEL_PREFIX = "confirmdel:"

DEFAULT_SHEET = "21 de agosto"

PRODUCTO, COSTO, CUOTAS, ELEGIR_HOJA, NOMBRE_HOJA, ELIMINAR_HOJA, CONFIRMAR_ELIMINAR = range(7)


def menu_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(BTN_TOTAL, callback_data=CB_TOTAL),
         InlineKeyboardButton(BTN_GASTOS, callback_data=CB_GASTOS)],
        [InlineKeyboardButton(BTN_PRODUCTOS, callback_data=CB_PRODUCTOS),
         InlineKeyboardButton(BTN_AGREGAR_CUOTA, callback_data=CB_AGREGAR_CUOTA)],
        [InlineKeyboardButton(BTN_HOJA_MENU, callback_data=CB_HOJA_MENU)],
    ])


def hoja_menu_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(BTN_ELEGIR_HOJA, callback_data=CB_HOJAS)],
        [InlineKeyboardButton(BTN_NUEVA_HOJA, callback_data=CB_NUEVA_HOJA)],
        [InlineKeyboardButton(BTN_ELIMINAR_HOJA, callback_data=CB_ELIMINAR_HOJA)],
        [InlineKeyboardButton("⬅️ Volver", callback_data=CB_CANCELAR)],
    ])


def cancelar_inline():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🚫 Cancelar", callback_data=CB_CANCELAR)]])


async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE, texto, reply_markup=None):
    markup = reply_markup if reply_markup is not None else menu_inline()
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(texto, parse_mode=PARSE_MODE, reply_markup=markup)
        except Exception:
            await update.callback_query.message.reply_text(texto, parse_mode=PARSE_MODE, reply_markup=markup)
    else:
        await update.message.reply_text(texto, parse_mode=PARSE_MODE, reply_markup=markup)


def get_sheet(context: ContextTypes.DEFAULT_TYPE):
    sh = gc.open_by_key(SHEET_ID)
    nombre_hoja = context.chat_data.get('hoja', DEFAULT_SHEET)
    try:
        return sh.worksheet(nombre_hoja)
    except gspread.exceptions.WorksheetNotFound:
        context.chat_data['hoja'] = DEFAULT_SHEET
        return sh.worksheet(DEFAULT_SHEET)


async def mostrar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await responder(update, context, "👋 <b>¿Qué quieres hacer?</b>")


async def hoja_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    actual = context.chat_data.get('hoja', DEFAULT_SHEET)
    await responder(
        update, context,
        f"📑 <b>Hojas</b>\n\n📍 Hoja actual: <b>{html.escape(actual)}</b>",
        reply_markup=hoja_menu_inline(),
    )


async def ver_total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ws = get_sheet(context)
        total = ws.acell('J2').value
        await responder(update, context, f"💰 <b>Total de gastos</b>\n{total}")
    except Exception as e:
        await responder(update, context, f"❌ Error: {html.escape(str(e))}")


async def ver_gastos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ws = get_sheet(context)
        columna_b = ws.col_values(2)[2:]  # Desde B3
        montos = [v for v in columna_b if v]
        total = ws.acell('J2').value

        if not montos:
            await responder(update, context, "📊 Aún no hay gastos registrados.")
            return

        lista = '\n'.join([f"{i}. {html.escape(str(g))}" for i, g in enumerate(montos, start=1)])
        await responder(
            update, context,
            f"📊 <b>Gastos registrados</b>\n\n{lista}\n\n💰 <b>Total:</b> {total}",
        )
    except Exception as e:
        await responder(update, context, f"❌ Error: {html.escape(str(e))}")


async def ver_productos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ws = get_sheet(context)
        filas = ws.get('D7:I200')

        bloques = []
        for fila in filas:
            if not fila or not fila[0]:
                continue
            producto = html.escape(str(fila[0]))
            costo = html.escape(str(fila[2])) if len(fila) > 2 and fila[2] else "—"
            cuota = html.escape(str(fila[4])) if len(fila) > 4 and fila[4] else "—"
            valor_cuota = html.escape(str(fila[5])) if len(fila) > 5 and fila[5] else "—"
            bloques.append(
                f"🛒 <b>{producto}</b>\n"
                f"   💵 Costo: {costo}\n"
                f"   📅 Cuota: {cuota}\n"
                f"   💳 Valor cuota: {valor_cuota}"
            )

        if not bloques:
            await responder(update, context, "📦 No hay productos en cuotas registrados.")
            return

        separador = "\n➖➖➖➖➖➖➖➖\n"
        texto = separador.join(bloques)
        await responder(update, context, f"📦 <b>Productos en cuotas</b>\n\n{texto}")
    except Exception as e:
        await responder(update, context, f"❌ Error: {html.escape(str(e))}")


async def agregar_cuota_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await responder(
        update, context,
        "🛒 <b>Nuevo producto en cuotas</b>\n\n"
        "1️⃣ ¿Cuál es el nombre del producto?",
        reply_markup=cancelar_inline(),
    )
    return PRODUCTO


async def recibir_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['producto'] = update.message.text
    await update.message.reply_text(
        f"✅ Producto: <b>{html.escape(update.message.text)}</b>\n\n"
        f"2️⃣ ¿Cuál es el costo total del producto?",
        parse_mode=PARSE_MODE,
        reply_markup=cancelar_inline(),
    )
    return COSTO


async def recibir_costo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        costo = float(update.message.text.replace(',', '.'))
    except ValueError:
        await update.message.reply_text(
            "❌ Envía solo un número para el costo",
            reply_markup=cancelar_inline(),
        )
        return COSTO

    context.user_data['costo'] = costo
    await update.message.reply_text(
        f"✅ Costo: <b>{costo:,.0f}</b>\n\n"
        f"3️⃣ ¿En cuántas cuotas?",
        parse_mode=PARSE_MODE,
        reply_markup=cancelar_inline(),
    )
    return CUOTAS


async def recibir_cuotas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cuotas = int(update.message.text)
        if cuotas <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Envía un número entero de cuotas",
            reply_markup=cancelar_inline(),
        )
        return CUOTAS

    producto = context.user_data['producto']
    costo = context.user_data['costo']
    valor_cuota = round(costo / cuotas)
    cuota_str = f"1/{cuotas}"

    try:
        ws = get_sheet(context)

        # Próxima fila libre de la tabla de cuotas (desde la fila 7)
        columna_d = ws.col_values(4)
        fila = len(columna_d) + 1
        if fila < 7:
            fila = 7

        ws.update_cell(fila, 4, producto)    # D
        ws.update_cell(fila, 6, costo)       # F
        ws.update_cell(fila, 8, cuota_str)    # H
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
            f"✅ <b>Producto agregado a cuotas</b>\n\n"
            f"🛒 <b>{html.escape(producto)}</b>\n"
            f"   💵 Costo: {costo:,.0f}\n"
            f"   📅 Cuota: {cuota_str}\n"
            f"   💳 Valor cuota: {valor_cuota:,.0f}\n\n"
            f"💰 Se sumó {valor_cuota:,.0f} a gastos.\n"
            f"<b>Total actual:</b> {total}",
            parse_mode=PARSE_MODE,
            reply_markup=menu_inline(),
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {html.escape(str(e))}",
            parse_mode=PARSE_MODE,
            reply_markup=menu_inline(),
        )

    context.user_data.clear()
    return ConversationHandler.END


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.chat_data.pop('hojas_disponibles', None)
    await responder(update, context, "🚫 Operación cancelada.")
    return ConversationHandler.END


async def elegir_hoja_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sh = gc.open_by_key(SHEET_ID)
        nombres = [w.title for w in sh.worksheets()]
        context.chat_data['hojas_disponibles'] = nombres

        actual = context.chat_data.get('hoja', DEFAULT_SHEET)
        botones = [
            [InlineKeyboardButton(("📍 " if n == actual else "") + n, callback_data=f"{CB_HOJA_PREFIX}{n}")]
            for n in nombres
        ]
        botones.append([InlineKeyboardButton("🚫 Cancelar", callback_data=CB_CANCELAR)])

        await responder(
            update, context,
            f"📑 <b>Hojas disponibles</b>\n\n"
            f"📍 Hoja actual: <b>{html.escape(actual)}</b>\n\n"
            f"Toca una hoja para seleccionarla.",
            reply_markup=InlineKeyboardMarkup(botones),
        )
        return ELEGIR_HOJA
    except Exception as e:
        await responder(update, context, f"❌ Error: {html.escape(str(e))}")
        return ConversationHandler.END


async def recibir_hoja(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    nombre = query.data[len(CB_HOJA_PREFIX):]
    nombres = context.chat_data.get('hojas_disponibles', [])

    if nombre not in nombres:
        await query.answer("Hoja no válida", show_alert=True)
        return ELEGIR_HOJA

    context.chat_data['hoja'] = nombre
    context.chat_data.pop('hojas_disponibles', None)
    await responder(
        update, context,
        f"✅ Ahora estás usando la hoja: <b>{html.escape(nombre)}</b>",
        reply_markup=hoja_menu_inline(),
    )
    return ConversationHandler.END


async def nueva_hoja_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await responder(
        update, context,
        "🗂️ <b>Nueva hoja mensual</b>\n\n"
        "Se duplicará la hoja actual: las cuotas avanzan en 1, las que ya terminaron "
        "se eliminan de la tabla, y los gastos se reinician dejando solo el valor de "
        "las cuotas vigentes.\n\n"
        "✏️ ¿Qué nombre le pones a la nueva hoja?",
        reply_markup=cancelar_inline(),
    )
    return NOMBRE_HOJA


async def recibir_nombre_hoja(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.message.text.strip()

    if not nombre:
        await update.message.reply_text("❌ Envía un nombre válido para la hoja", reply_markup=cancelar_inline())
        return NOMBRE_HOJA

    try:
        sh = gc.open_by_key(SHEET_ID)
        existentes = [w.title for w in sh.worksheets()]
        if nombre in existentes:
            await update.message.reply_text(
                "❌ Ya existe una hoja con ese nombre, envía otro",
                reply_markup=cancelar_inline(),
            )
            return NOMBRE_HOJA

        ws_actual = get_sheet(context)
        filas_originales = ws_actual.get('D7:I200')

        nueva_ws = ws_actual.duplicate(new_sheet_name=nombre)

        sobrevivientes = []
        completadas = 0
        total_filas_originales = 0

        for fila in filas_originales:
            if not fila or not fila[0]:
                continue
            total_filas_originales += 1

            producto = fila[0]
            costo = fila[2] if len(fila) > 2 else ""
            cuota_str = fila[4] if len(fila) > 4 else ""
            valor_cuota = fila[5] if len(fila) > 5 else ""

            try:
                actual, maximo = cuota_str.split('/')
                nueva_actual = int(actual) + 1
                maximo = int(maximo)
            except (ValueError, AttributeError):
                sobrevivientes.append((producto, costo, cuota_str, valor_cuota))
                continue

            if nueva_actual > maximo:
                completadas += 1
                continue

            sobrevivientes.append((producto, costo, f"{nueva_actual}/{maximo}", valor_cuota))

        # Limpia toda la tabla de cuotas y de gastos antes de reescribir
        nueva_ws.batch_clear(['D7:I200', 'B3:B1000'])

        for i, (producto, costo, cuota_str, valor_cuota) in enumerate(sobrevivientes):
            fila_num = 7 + i
            nueva_ws.update_cell(fila_num, 4, producto)
            nueva_ws.update_cell(fila_num, 6, costo)
            nueva_ws.update_cell(fila_num, 8, cuota_str)
            nueva_ws.update_cell(fila_num, 9, valor_cuota)
            nueva_ws.merge_cells(f'D{fila_num}:E{fila_num}')
            nueva_ws.merge_cells(f'F{fila_num}:G{fila_num}')

            fila_gasto = 3 + i
            nueva_ws.update_cell(fila_gasto, 2, valor_cuota)

        context.chat_data['hoja'] = nombre
        context.chat_data.pop('hojas_disponibles', None)

        await update.message.reply_text(
            f"✅ <b>Hoja creada:</b> {html.escape(nombre)}\n\n"
            f"📅 Cuotas avanzadas: <b>{len(sobrevivientes)}</b>\n"
            f"🏁 Cuotas completadas y eliminadas: <b>{completadas}</b>\n"
            f"📊 Gastos reiniciados con el valor de las cuotas vigentes.\n\n"
            f"📍 Ahora estás usando esta hoja.",
            parse_mode=PARSE_MODE,
            reply_markup=menu_inline(),
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {html.escape(str(e))}",
            parse_mode=PARSE_MODE,
            reply_markup=menu_inline(),
        )

    return ConversationHandler.END


async def eliminar_hoja_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sh = gc.open_by_key(SHEET_ID)
        nombres = [w.title for w in sh.worksheets()]
        context.chat_data['hojas_disponibles'] = nombres

        if len(nombres) <= 1:
            await responder(
                update, context,
                "❌ No puedes eliminar la única hoja que existe.",
                reply_markup=hoja_menu_inline(),
            )
            return ConversationHandler.END

        botones = [
            [InlineKeyboardButton(f"🗑️ {n}", callback_data=f"{CB_DELHOJA_PREFIX}{n}")]
            for n in nombres
        ]
        botones.append([InlineKeyboardButton("🚫 Cancelar", callback_data=CB_CANCELAR)])

        await responder(
            update, context,
            "🗑️ <b>Eliminar hoja</b>\n\nToca la hoja que quieres eliminar.",
            reply_markup=InlineKeyboardMarkup(botones),
        )
        return ELIMINAR_HOJA
    except Exception as e:
        await responder(update, context, f"❌ Error: {html.escape(str(e))}")
        return ConversationHandler.END


async def recibir_eliminar_hoja(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    nombre = query.data[len(CB_DELHOJA_PREFIX):]
    nombres = context.chat_data.get('hojas_disponibles', [])

    if nombre not in nombres:
        await query.answer("Hoja no válida", show_alert=True)
        return ELIMINAR_HOJA

    botones = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Sí, eliminar", callback_data=f"{CB_CONFIRMDEL_PREFIX}{nombre}")],
        [InlineKeyboardButton("🚫 Cancelar", callback_data=CB_CANCELAR)],
    ])
    await responder(
        update, context,
        f"⚠️ <b>¿Eliminar la hoja \"{html.escape(nombre)}\"?</b>\n\n"
        f"Esta acción no se puede deshacer.",
        reply_markup=botones,
    )
    return CONFIRMAR_ELIMINAR


async def confirmar_eliminar_hoja(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    nombre = query.data[len(CB_CONFIRMDEL_PREFIX):]

    try:
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.worksheet(nombre)
        sh.del_worksheet(ws)

        if context.chat_data.get('hoja') == nombre:
            restantes = [w.title for w in sh.worksheets()]
            context.chat_data['hoja'] = DEFAULT_SHEET if DEFAULT_SHEET in restantes else restantes[0]

        context.chat_data.pop('hojas_disponibles', None)
        await responder(
            update, context,
            f"🗑️ Hoja <b>{html.escape(nombre)}</b> eliminada.\n\n"
            f"📍 Hoja actual: <b>{html.escape(context.chat_data.get('hoja', DEFAULT_SHEET))}</b>",
            reply_markup=hoja_menu_inline(),
        )
    except Exception as e:
        await responder(update, context, f"❌ Error: {html.escape(str(e))}", reply_markup=hoja_menu_inline())

    return ConversationHandler.END


async def recibir_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        monto = float(update.message.text)
        ws = get_sheet(context)

        columna_b = ws.col_values(2)
        fila = len(columna_b) + 1
        if fila < 3:
            fila = 3

        ws.update_cell(fila, 2, monto)

        total = ws.acell('J2').value
        await update.message.reply_text(
            f"✅ Agregado: <b>{monto:,.0f}</b>\n\n💰 <b>Total:</b> {total}",
            parse_mode=PARSE_MODE,
            reply_markup=menu_inline(),
        )
    except ValueError:
        await mostrar_menu(update, context)
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {html.escape(str(e))}",
            parse_mode=PARSE_MODE,
            reply_markup=menu_inline(),
        )


async def post_init(application: Application):
    # Sin comandos en el menú de Telegram: solo botones inline en el chat
    await application.bot.set_my_commands([])


if __name__ == '__main__':
    app = Application.builder().token(token).post_init(post_init).build()

    app.add_handler(CallbackQueryHandler(ver_total, pattern=f"^{CB_TOTAL}$"))
    app.add_handler(CallbackQueryHandler(ver_gastos, pattern=f"^{CB_GASTOS}$"))
    app.add_handler(CallbackQueryHandler(ver_productos, pattern=f"^{CB_PRODUCTOS}$"))
    app.add_handler(CallbackQueryHandler(hoja_menu, pattern=f"^{CB_HOJA_MENU}$"))

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(agregar_cuota_start, pattern=f"^{CB_AGREGAR_CUOTA}$")],
        states={
            PRODUCTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_producto)],
            COSTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_costo)],
            CUOTAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_cuotas)],
        },
        fallbacks=[
            CommandHandler("cancelar", cancelar),
            CallbackQueryHandler(cancelar, pattern=f"^{CB_CANCELAR}$"),
        ],
    )
    app.add_handler(conv_handler)

    hoja_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(elegir_hoja_start, pattern=f"^{CB_HOJAS}$")],
        states={
            ELEGIR_HOJA: [CallbackQueryHandler(recibir_hoja, pattern=f"^{CB_HOJA_PREFIX}")],
        },
        fallbacks=[
            CommandHandler("cancelar", cancelar),
            CallbackQueryHandler(cancelar, pattern=f"^{CB_CANCELAR}$"),
        ],
    )
    app.add_handler(hoja_handler)

    nueva_hoja_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(nueva_hoja_start, pattern=f"^{CB_NUEVA_HOJA}$")],
        states={
            NOMBRE_HOJA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nombre_hoja)],
        },
        fallbacks=[
            CommandHandler("cancelar", cancelar),
            CallbackQueryHandler(cancelar, pattern=f"^{CB_CANCELAR}$"),
        ],
    )
    app.add_handler(nueva_hoja_handler)

    eliminar_hoja_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(eliminar_hoja_start, pattern=f"^{CB_ELIMINAR_HOJA}$")],
        states={
            ELIMINAR_HOJA: [CallbackQueryHandler(recibir_eliminar_hoja, pattern=f"^{CB_DELHOJA_PREFIX}")],
            CONFIRMAR_ELIMINAR: [CallbackQueryHandler(confirmar_eliminar_hoja, pattern=f"^{CB_CONFIRMDEL_PREFIX}")],
        },
        fallbacks=[
            CommandHandler("cancelar", cancelar),
            CallbackQueryHandler(cancelar, pattern=f"^{CB_CANCELAR}$"),
        ],
    )
    app.add_handler(eliminar_hoja_handler)

    # Fuera de cualquier conversación: botón "Volver" del submenú de hojas
    app.add_handler(CallbackQueryHandler(cancelar, pattern=f"^{CB_CANCELAR}$"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=token,
        webhook_url=f"{RENDER_URL}/{token}"
    )
