from telethon.sync import TelegramClient
from telethon import events
import os
import pickle
import asyncio

api_id = '21963510'  # Stesso api_id di add.py
api_hash = 'eddfccf6e4ea21255498028e5af25eb1'  # Stesso api_hash di add.py

# ID utente autorizzato
AUTHORIZED_USER_ID = 6849853752  # Sostituisci con il tuo ID Telegram

# Cartella delle sessioni
SESSIONS_FOLDER = "sessions"

# Carica i numeri di telefono salvati in vars.txt
def load_sessions():
    if not os.path.exists("vars.txt"):
        return []
    
    with open("vars.txt", "rb") as f:
        accounts = []
        while True:
            try:
                account = pickle.load(f)
                accounts.extend(account)
            except EOFError:
                break
        return accounts

# Inizializza i client per tutte le sessioni salvate
def initialize_clients():
    sessions = load_sessions()
    clients = []
    
    for phone_number in sessions:
        session_path = f"{SESSIONS_FOLDER}/{phone_number}"
        client = TelegramClient(session_path, api_id, api_hash)
        client.start()
        clients.append(client)
        print(f"Client attivato per: {phone_number}")
    
    return clients

# Funzione per ottenere una lista di gruppi e canali
async def list_groups(client):
    dialogs = await client.get_dialogs()
    group_list = []
    for dialog in dialogs:
        if dialog.is_group or dialog.is_channel:
            group_list.append((dialog.title, dialog.entity.id))
    return group_list

# Funzione per scaricare i messaggi da un gruppo
async def download_group_messages(client, group_id, group_title):
    messages_text = []
    async for message in client.iter_messages(group_id):
        sender_id = message.sender_id
        text = message.message or ""
        messages_text.append(f"{sender_id}: {text}")
    
    # Salva i messaggi in un file
    filename = f"{group_title.replace(' ', '_')}_messages.txt"
    with open(filename, "w", encoding="utf-8") as file:
        file.write("\n".join(messages_text))
    return filename

# Funzione principale per gestire i comandi
def start_bot(client):
    @client.on(events.NewMessage(pattern="/lista"))
    async def list_handler(event):
        if event.sender_id != AUTHORIZED_USER_ID:
            return  # Ignora i messaggi di utenti non autorizzati

        groups = await list_groups(client)
        if not groups:
            await event.reply("Non sono unito a nessun gruppo.")
            return
        
        message = "Ecco i gruppi a cui sono unito:\n"
        for idx, (title, group_id) in enumerate(groups, start=1):
            message += f"{idx}. {title} (ID: {group_id})\n"
        await event.reply(message)

    @client.on(events.NewMessage(pattern=r"/see (\d+)"))
    async def see_handler(event):
        if event.sender_id != AUTHORIZED_USER_ID:
            return  # Ignora i messaggi di utenti non autorizzati
        
        index = int(event.pattern_match.group(1))
        groups = await list_groups(client)
        
        if index < 1 or index > len(groups):
            await event.reply("Indice non valido. Usa /lista per vedere i gruppi disponibili.")
            return
        
        group_title, group_id = groups[index - 1]
        await event.reply(f"Sto scaricando i messaggi del gruppo: {group_title}. Attendi...")
        
        filename = await download_group_messages(client, group_id, group_title)
        await client.send_file(AUTHORIZED_USER_ID, filename, caption=f"Messaggi del gruppo: {group_title}")
        os.remove(filename)

    print("Bot avviato e in ascolto...")
    client.run_until_disconnected()

if __name__ == "__main__":
    clients = initialize_clients()
    
    if not clients:
        print("Nessuna sessione disponibile. Esegui add.py per aggiungere un account.")
    else:
        for client in clients:
            asyncio.run(start_bot(client))
