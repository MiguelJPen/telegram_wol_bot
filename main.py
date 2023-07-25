from pyrogram import Client, idle, filters
import os
import pickle
from pyrogram.types import BotCommand, Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from wakeonlan import send_magic_packet

from custom_filters import whitelist_filter, callback_data_filter
from utils import load_hosts, parse_host_info, save_hosts, build_host_list_markup, check_if_up

api_id = os.environ["API_ID"]
api_hash = os.environ["API_HASH"]
try:
    bot_token = os.environ["BOT_TOKEN"]
except KeyError:
    bot_token = None
try:
    session_str = os.environ["SESSION_STR"]
except KeyError:
    session_str = None

if session_str:
    app = Client("tg_wol", session_string=session_str)
else:
    app = Client("tg_wol", api_id=api_id, api_hash=api_hash, bot_token=bot_token, in_memory=True)


async def main():
    async with app:
        if not session_str:
            s_str = await app.export_session_string()
            print("Please save session string and use it in the future:")
            print(s_str)
        else:
            # Setting bot commands
            await app.set_bot_commands([
                BotCommand("start", "Usa este comando si el bot no responde"),
                BotCommand("add_host", "Añade un nuevo ordenador a la lista"),
                BotCommand("remove_host", "Elimina un ordenador de la lista"),
                BotCommand("list_hosts", "Enumera los ordenadores en la lista"),
                BotCommand("wake_host", "Enciende un ordenador"),
            ])
            print("Bot is running")
            await idle()


@app.on_message(filters.command("start") & whitelist_filter)
async def welcome(_client: Client, message: Message):
    await message.reply_text("¡Bienvenido!")


@app.on_message(filters.command("add_host") & whitelist_filter)
async def add_host(_client: Client, message: Message):
    m = "Por favor, envía los detalles del ordenador en el siguiente formato:\n" \
        "Nombre (solo para ser identificado en la lista)\n" \
        "Dirección MAC\n" \
        "Dirección IP\n" \
        "Ejemplo:\n" \
        "rogpc\n2C:54:91:88:C9:E3\n192.168.50.23"
    await message.reply_text(m)


@app.on_message(filters.command("remove_host") & whitelist_filter)
async def remove_host(client: Client, message: Message):
    await client.send_message(message.chat.id, "Por favor selecciona el ordenador a eliminar:",
                              reply_markup=build_host_list_markup("remove"))


@app.on_message(filters.command("list_hosts") & whitelist_filter)
async def list_hosts(client: Client, message: Message):
    m = ""
    host_list = load_hosts("hosts.pkl")
    for host in host_list:
        m += f"**{host['name']}**\n"
        m += f"MAC: {host['mac']}\n"
        m += f"IP: {host['ip']}\n"
        if check_if_up(host['ip']):
            m += "El ordenador está encendido!\n"
        else:
            m += "El ordenador está apagado\n"
        m += "\n"
    if m == "":
        m += "No hay ningún ordenador guardado"
    await message.reply_text(m)


@app.on_message(filters.command("wake_host") & whitelist_filter)
async def wake_host(client: Client, message: Message):
    await client.send_message(message.chat.id, "¿Qué ordenador quieres encender?",
                              reply_markup=build_host_list_markup("wake"))


@app.on_callback_query(callback_data_filter(None, "remove") & whitelist_filter)
async def remove_host_callback(_client: Client, callback_query: CallbackQuery):
    hostname = callback_query.data.split("_")[1]
    host_list = load_hosts("hosts.pkl")
    new_host_list = [h for h in host_list if h["name"] != hostname]
    save_hosts("hosts.pkl", new_host_list)
    await callback_query.edit_message_text(f"¡Se ha eliminado {hostname} satisfactoriamente!")


@app.on_callback_query(callback_data_filter(None, "wake") & whitelist_filter)
async def wake_host_callback(_client: Client, callback_query: CallbackQuery):
    hostname = callback_query.data.split("_")[1]
    host_list = load_hosts("hosts.pkl")
    host = [h for h in host_list if h["name"] == hostname][0]
    if check_if_up(host['ip']):
        await callback_query.edit_message_text(f"¡El ordenador {hostname} ya está encendido!")
    else:
        mac_parsed = host["mac"].replace(":", ".")
        send_magic_packet(mac_parsed)
        await callback_query.edit_message_text(f"¡Se ha enviado un paquete mágico a {hostname}!")


@app.on_message(whitelist_filter)
async def handle_host_info(_client: Client, message: Message):
    host_list = load_hosts("hosts.pkl")
    host_info = parse_host_info(message.text)
    if host_info:
        host_list.append(host_info)
        save_hosts("hosts.pkl", host_list)
        await message.reply_text("¡Se ha añadido el ordenador correctamente!")
    else:
        await message.reply_text("¡Los valores son incorrectos!")


app.run(main())
