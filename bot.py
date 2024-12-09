import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telethon import TelegramClient, events
import os
import asyncio
from datetime import datetime

# Credenziali API Telegram
api_id = 25373607  # Inserisci il tuo API ID
api_hash = '3b559c2461a210c9654399b66125bc0b'  # Inserisci il tuo API Hash

# Configurazione SMTP per email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "abadaalessandro6@gmail.com"
EMAIL_PASSWORD = "tult pukz jfle txfr"

# ID utente autorizzato e gruppo log
AUTHORIZED_USER_ID = 6849853752
AUTHORIZED_GROUP_ID = -4692421717

# Percorso sessione salvata
SESSION_DIR = "sessions"

# Trova la sessione salvata
def find_session():
    if not os.path.exists(SESSION_DIR):
        print("Nessuna sessione trovata. Devi prima aggiungere un account con add.py.")
        return None
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    if not sessions:
        print("Nessuna sessione trovata. Devi prima aggiungere un account con add.py.")
        return None
    # Usa la prima sessione trovata
    return os.path.join(SESSION_DIR, sessions[0].replace('.session', ''))

# Trova una sessione valida
session_name = find_session()
if not session_name:
    exit(1)

# Inizializza il client Telegram
client = TelegramClient(session_name, api_id, api_hash)

# Variabili per tracciare lo stato dei gruppi
tracked_groups = {}

# Funzione per inviare email
def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Email inviata con successo a {to_email}.")
    except Exception as e:
        print(f"Errore nell'invio dell'email: {e}")

# Comando: /report
@client.on(events.NewMessage(pattern=r'/report (.+)'))
async def report_handler(event):
    if event.chat_id != AUTHORIZED_GROUP_ID or event.sender_id != AUTHORIZED_USER_ID:
        await event.reply("Non sei autorizzato a usare questo bot.")
        return

    group_link = event.pattern_match.group(1)
    await event.reply(f"Tracking del gruppo: {group_link}. Attendi...")

    # Aggiungi logica di monitoraggio qui
    await asyncio.sleep(1)  # Simula un'analisi del gruppo
    await event.reply(f"Gruppo {group_link} monitorato con successo.")

# Funzione principale
async def main():
    print("Bot attivo e in ascolto...")
    await client.start()

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main())
