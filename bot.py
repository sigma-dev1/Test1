import asyncio
import os
from datetime import datetime, timedelta
import sqlite3
from telethon import TelegramClient, events
from telethon.errors import ChannelInvalidError

# Configurazioni
api_id = 25373607  # Tuo API ID
api_hash = "3b559c2461a210c9654399b66125bc0b"  # Tuo API Hash
AUTHORIZED_USER_ID = 6849853752  # Il tuo ID utente Telegram

# Nome del database SQLite
DB_NAME = "groups.db"

# Inizializza il client Telegram
client = TelegramClient("bot", api_id, api_hash)


# Funzione per creare il database se non esiste
def create_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tracked_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_username TEXT UNIQUE,
            status TEXT,
            last_check TIMESTAMP,
            reported_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# Funzione per aggiungere un gruppo al database
def add_group_to_db(group_username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute("""
        INSERT OR IGNORE INTO tracked_groups (group_username, status, last_check, reported_at)
        VALUES (?, ?, ?, ?)
    """, (group_username, "active", now, now))
    conn.commit()
    conn.close()


# Funzione per aggiornare lo stato di un gruppo nel database
def update_group_status(group_username, status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute("""
        UPDATE tracked_groups
        SET status = ?, last_check = ?
        WHERE group_username = ?
    """, (status, now, group_username))
    conn.commit()
    conn.close()


# Funzione per recuperare tutti i gruppi dal database
def get_all_groups():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tracked_groups")
    groups = cursor.fetchall()
    conn.close()
    return groups


# Funzione per eliminare un gruppo dal database
def remove_group_from_db(group_username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tracked_groups WHERE group_username = ?", (group_username,))
    conn.commit()
    conn.close()


# Funzione per verificare se un gruppo è attivo o bannato
async def check_group_status(group_username):
    try:
        await client.get_entity(group_username)
        return "active"
    except ChannelInvalidError:
        return "banned"
    except Exception as e:
        print(f"Errore durante il controllo del gruppo @{group_username}: {e}")
        return "unknown"


# Comando /start
@client.on(events.NewMessage(pattern=r"/start"))
async def start_handler(event):
    if event.sender_id == AUTHORIZED_USER_ID:
        await event.reply("Ciao! Sono attivo. Usa /report <username> per segnalare un gruppo o /lista per vedere i gruppi monitorati.")
    else:
        await event.reply("Non sei autorizzato a usare questo bot.")


# Comando /report <username>
@client.on(events.NewMessage(pattern=r"/report (.+)"))
async def report_handler(event):
    if event.sender_id != AUTHORIZED_USER_ID:
        return

    group_username = event.pattern_match.group(1).strip()
    await event.reply(f"Segnalando il gruppo @{group_username}...")

    try:
        # Verifica se il gruppo esiste
        await client.get_entity(group_username)
        add_group_to_db(group_username)
        await event.reply(f"Il gruppo @{group_username} è stato segnalato e ora è monitorato.")
    except Exception as e:
        await event.reply(f"Errore: impossibile segnalare il gruppo @{group_username}. {e}")


# Comando /lista
@client.on(events.NewMessage(pattern=r"/lista"))
async def list_handler(event):
    if event.sender_id != AUTHORIZED_USER_ID:
        return

    groups = get_all_groups()
    if not groups:
        await event.reply("Nessun gruppo monitorato al momento.")
        return

    message = "Gruppi monitorati:\n"
    for group in groups:
        group_username, status, last_check, reported_at = group[1], group[2], group[3], group[4]
        message += f"- @{group_username}: {status} (Ultimo controllo: {last_check}, Segnalato: {reported_at})\n"

    await event.reply(message)


# Funzione per monitorare periodicamente i gruppi
async def monitor_groups():
    while True:
        print("Controllo lo stato dei gruppi monitorati...")
        groups = get_all_groups()
        now = datetime.now()

        for group in groups:
            group_username, status, last_check, reported_at = group[1], group[2], group[3], group[4]

            # Controlla lo stato del gruppo
            new_status = await check_group_status(group_username)

            if new_status != status:
                update_group_status(group_username, new_status)

                # Notifica l'utente
                if new_status == "banned":
                    time_banned = now - datetime.strptime(reported_at, "%Y-%m-%d %H:%M:%S")
                    await client.send_message(
                        AUTHORIZED_USER_ID,
                        f"Il gruppo @{group_username} è stato bannato. Tempo bannato: {time_banned}."
                    )
                elif new_status == "active":
                    await client.send_message(
                        AUTHORIZED_USER_ID,
                        f"Il gruppo @{group_username} è stato sbannato. Riprovo a segnalarlo..."
                    )
                    # Riprova a segnalare il gruppo
                    add_group_to_db(group_username)

            # Notifica se il gruppo non è stato bannato entro 2 settimane
            if status == "active" and (now - datetime.strptime(reported_at, "%Y-%m-%d %H:%M:%S")) > timedelta(weeks=2):
                await client.send_message(
                    AUTHORIZED_USER_ID,
                    f"Il gruppo @{group_username} non è stato bannato entro 2 settimane. Segnalazione non riuscita."
                )
                remove_group_from_db(group_username)

        await asyncio.sleep(10800)  # Aspetta 3 ore prima del prossimo controllo


# Funzione principale
async def main():
    create_database()  # Crea il database se non esiste
    print("Bot avviato e in ascolto...")
    await client.start()
    client.loop.create_task(monitor_groups())
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
