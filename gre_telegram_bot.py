from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os

# Obtener el token de la variable de entorno
TOKEN = os.getenv("TOKEN")

# Variables globales
datos = {}
estado = {}

# Inicio del bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Soy el bot de Gestión de Riesgo en Entrada (GRE).\nPor favor, indica si la operación es 'long' o 'short'."
    )
    estado[update.effective_user.id] = "tipo_operacion"

# Procesar mensajes
async def procesar_datos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    texto = update.message.text.strip().lower().replace(",", ".")

    try:
        if estado.get(user_id) == "tipo_operacion":
            if texto in ["long", "short"]:
                datos[user_id] = {"tipo_operacion": texto}
                estado[user_id] = "precio_entrada"
                await update.message.reply_text("Perfecto, ahora dime el precio de entrada.")
            else:
                await update.message.reply_text("Por favor, indica 'long' o 'short'.")
        elif estado.get(user_id) == "precio_entrada":
            datos[user_id]["precio_entrada"] = float(texto)
            estado[user_id] = "tokens_iniciales"
            await update.message.reply_text("Dime la cantidad de tokens en la entrada.")
        elif estado.get(user_id) == "tokens_iniciales":
            datos[user_id]["tokens_iniciales"] = float(texto)
            estado[user_id] = "capital_total"
            await update.message.reply_text("Dime el capital total de la cuenta (USD).")
        elif estado.get(user_id) == "capital_total":
            datos[user_id]["capital_total"] = float(texto)
            estado[user_id] = "porcentaje_riesgo"
            await update.message.reply_text("Dime el porcentaje de riesgo sobre el capital total.")
        elif estado.get(user_id) == "porcentaje_riesgo":
            datos[user_id]["porcentaje_riesgo"] = float(texto)
            estado[user_id] = "porcentaje_stop_loss"
            await update.message.reply_text("Dime el porcentaje de stop loss basado en el precio de entrada.")
        elif estado.get(user_id) == "porcentaje_stop_loss":
            datos[user_id]["porcentaje_stop_loss"] = float(texto)
            estado[user_id] = "niveles_recompra"
            await update.message.reply_text("Dime la cantidad de niveles de recompra.")
        elif estado.get(user_id) == "niveles_recompra":
            datos[user_id]["niveles_recompra"] = int(texto)
            estado[user_id] = "niveles_take_profit"
            await update.message.reply_text("Dime la cantidad de niveles de take profit.")
        elif estado.get(user_id) == "niveles_take_profit":
            datos[user_id]["niveles_take_profit"] = int(texto)
            estado[user_id] = "porcentaje_take_profit"
            await update.message.reply_text("Dime el porcentaje de diferencia entre niveles de take profit.")
        elif estado.get(user_id) == "porcentaje_take_profit":
            datos[user_id]["porcentaje_take_profit"] = float(texto)
            estado[user_id] = None
            await calcular_resultados(update, datos[user_id])
        else:
            await update.message.reply_text("Algo salió mal. Intenta de nuevo con /start.")
    except ValueError as e:
        await update.message.reply_text(f"Error: {e}. Por favor, introduce un número válido.")
    except Exception as e:
        await update.message.reply_text("Ocurrió un error inesperado. Por favor, inténtalo de nuevo más tarde.")

async def calcular_resultados(update: Update, datos: dict):
    try:
        # Variables de entrada
        tipo_operacion = datos["tipo_operacion"]
        precio_entrada = datos["precio_entrada"]
        tokens_iniciales = datos["tokens_iniciales"]
        capital_total = datos["capital_total"]
        porcentaje_riesgo = datos["porcentaje_riesgo"]
        porcentaje_stop_loss = datos["porcentaje_stop_loss"]
        niveles_recompra = datos["niveles_recompra"]
        niveles_take_profit = datos["niveles_take_profit"]
        porcentaje_take_profit = datos["porcentaje_take_profit"]

        # Calcular riesgo máximo
        riesgo_maximo = capital_total * (porcentaje_riesgo / 100)

        # Calcular Stop Loss Global
        if tipo_operacion == "long":
            stop_loss = round(precio_entrada - (porcentaje_stop_loss / 100) * precio_entrada, 8)
        else:  # short
            stop_loss = round(precio_entrada + (porcentaje_stop_loss / 100) * precio_entrada, 8)

        # Calcular niveles de recompra
        precios_recompra = [
            round(precio_entrada + i * ((stop_loss - precio_entrada) / (niveles_recompra + 1)), 8)
            for i in range(1, niveles_recompra + 1)
        ]
        
        # Ajustar el último nivel de recompra para estar 0.75% debajo del Stop Loss (en short)
        if tipo_operacion == "short":
            precios_recompra[-1] = round(stop_loss * (1 - 0.0075), 8)

        # Tokens por recompra distribuidos en Martingale
        tokens_recompra = [round(tokens_iniciales * (1.5 ** i), 6) for i in range(niveles_recompra)]

        # Total tokens después de recompras
        total_tokens = tokens_iniciales + sum(tokens_recompra)

        # Calcular niveles de take profit
        precios_take_profit = [
            round(precio_entrada - i * ((porcentaje_take_profit / 100) * precio_entrada), 8)
            for i in range(1, niveles_take_profit + 1)
        ]
        tokens_take_profit = [
            round(total_tokens * nivel / sum(range(1, niveles_take_profit + 1)), 6)
            for nivel in range(1, niveles_take_profit + 1)
        ]

        # Formatear resultados escapando caracteres especiales
        resultados = (
            f"*Resultados de Gestión de Riesgo en Entrada (GRE):*\n\n"
            f"*Datos Ingresados:*\n"
            f"- Tipo de operación: {tipo_operacion}\n"
            f"- Precio de entrada: {precio_entrada}\n"
            f"- Cantidad inicial de tokens: {tokens_iniciales}\n"
            f"- Capital total: {capital_total}\n"
            f"- Porcentaje de riesgo: {porcentaje_riesgo}\n"
            f"- Porcentaje de stop loss: {porcentaje_stop_loss}\n"
            f"- Niveles de recompra: {niveles_recompra}\n"
            f"- Niveles de take profit: {niveles_take_profit}\n"
            f"- Porcentaje de take profit: {porcentaje_take_profit}\n\n"
            f"*Riesgo Máximo Permitido:* {riesgo_maximo:.2f} USD\n\n"
            f"*Stop Loss Global:* {stop_loss}\n\n"
            f"*Niveles de Recompra:*\n"
        )
        for i, (precio, tokens) in enumerate(zip(precios_recompra, tokens_recompra)):
            resultados += f"- Nivel {i + 1}: Precio {precio}, Tokens {tokens}\n"

        resultados += "\n*Niveles de Take Profit:*\n"
        for i, (precio, tokens) in enumerate(zip(precios_take_profit, tokens_take_profit)):
            resultados += f"- Nivel {i + 1}: Precio {precio}, Tokens {tokens}\n"

        # Escapar caracteres reservados en MarkdownV2
        resultados = resultados.replace("(", "\\(").replace(")", "\\)").replace("-", "\\-").replace(".", "\\.")

        # Enviar resultados
        await update.message.reply_text(resultados, parse_mode="MarkdownV2")

    except Exception as e:
        await update.message.reply_text(f"Error al calcular resultados: {e}")

# Configuración del bot
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_datos))

print("Bot GRE en ejecución...")
app.run_polling()
