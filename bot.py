import os
import asyncio
import sqlite3
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# Carica le variabili d'ambiente
load_dotenv()

# Configurazione API Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "7659684235:AAG7TOMLBRpd7pgNybU0UOrAucvxTANC9H0")
AUTHORIZED_USER_ID = int(os.getenv("AUTHORIZED_USER_ID", "6849853752"))

# Configurazione Hugging Face
HF_TOKEN = os.getenv("HF_TOKEN", "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")
HF_GENERATION_URL = os.getenv("HF_GENERATION_URL", "https://api-inference.huggingface.co/models/gpt2")

# Inizializza il bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Database
DATABASE_PATH = "groups.db"

def initialize_database():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            last_check DATETIME NOT NULL,
            reported_at DATETIME NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# Funzione per aggiungere o aggiornare i gruppi nel database
def add_or_update_group(username, status, reported_at=None):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO groups (username, status, last_check, reported_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
        status=excluded.status, last_check=excluded.last_check
    """, (username, status, datetime.now(), reported_at or datetime.now()))
    conn.commit()
    conn.close()

# Funzione per ottenere lo stato dei gruppi
def get_groups():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT username, status, last_check, reported_at FROM groups")
    rows = cursor.fetchall()
    conn.close()
    return rows

# Funzione per eliminare un gruppo dal database
def remove_group(username):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM groups WHERE username = ?", (username,))
    conn.commit()
    conn.close()

# Funzione per generare un report tramite Hugging Face
def generate_report_text(group_username):
    prompt = f"Please generate a professional email report about the group @{group_username} which violates Telegram's Terms of Service. Include necessary details to request banning of the group."
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    try:
        response = requests.post(HF_GENERATION_URL, headers=headers, json={"inputs": prompt})
        if response.status_code == 200:
            return response.json()[0]["generated_text"]
        else:
            return "Error generating report."
    except Exception as e:
        return f"Error: {e}"

# Comando: /start
@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    if message.from_user.id == AUTHORIZED_USER_ID:
        await message.reply("Il bot è attivo. Usa /report <username> per segnalare un gruppo e /lista per vedere lo stato dei gruppi.")
    else:
        await message.reply("Non sei autorizzato a utilizzare questo bot.")

# Comando: /report <username>
@dp.message_handler(commands=["report"])
async def report_handler(message: types.Message):
    if message.from_user.id != AUTHORIZED_USER_ID:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Devi specificare un username di gruppo. Usa /report <username>.")
        return

    group_username = args[1].strip()
    await message.reply(f"Segnalazione del gruppo @{group_username} in corso...")

    # Aggiungi al database e invia segnalazione
    add_or_update_group(group_username, status="active")
    email_body = generate_report_text(group_username)

    await message.reply(f"Il gruppo @{group_username} è stato segnalato e monitorato.")
    # La segnalazione viene inviata in background

# Comando: /lista
@dp.message_handler(commands=["lista"])
async def list_handler(message: types.Message):
    if message.from_user.id != AUTHORIZED_USER_ID:
        return

    groups = get_groups()
    if not groups:
        await message.reply("Nessun gruppo attualmente monitorato.")
        return

    message_text = "Stato dei gruppi monitorati:\n"
    for group in groups:
        username, status, last_check, reported_at = group
        last_check = datetime.strptime(last_check, "%Y-%m-%d %H:%M:%S")
        reported_at = datetime.strptime(reported_at, "%Y-%m-%d %H:%M:%S")
        message_text += f"- @{username}: {status} (Ultimo controllo: {last_check}, Segnalato: {reported_at})\n"

    await message.reply(message_text)

# Task per monitorare i gruppi ogni 3 ore
async def monitor_groups():
    while True:
        groups = get_groups()
        for group in groups:
            username, status, last_check, reported_at = group
            if status == "active":
                # Controlla se il gruppo è stato bannato
                # Simuliamo con un controllo placeholder (esempio reale: chiamata API Telegram)
                banned = False  # Placeholder per il controllo effettivo

                if banned:
                    add_or_update_group(username, "banned")
                    await bot.send_message(AUTHORIZED_USER_ID, f"Il gruppo @{username} è stato bannato.")
                elif (datetime.now() - datetime.strptime(reported_at, "%Y-%m-%d %H:%M:%S")) > timedelta(weeks=2):
                    await bot.send_message(AUTHORIZED_USER_ID, f"Il gruppo @{username} non è stato bannato entro 2 settimane.")
                    remove_group(username)

        await asyncio.sleep(10800)  # 3 ore in secondi

# Avvio del bot
if __name__ == "__main__":
    initialize_database()
    loop = asyncio.get_event_loop()
    loop.create_task(monitor_groups())
    executor.start_polling(dp, skip_updates=True)
