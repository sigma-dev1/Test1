import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, PhoneNumberInvalidError
import requests
import asyncio
from datetime import datetime

# Credenziali API di Telegram
api_id = 25373607  # Inserisci il tuo API ID
api_hash = '3b559c2461a210c9654399b66125bc0b'  # Inserisci il tuo API Hash

# Configurazione SMTP per email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "abadaalessandro6@gmail.com"  # Email che invia le segnalazioni
EMAIL_PASSWORD = "tult pukz jfle txfr"  # Password o password per app

# Inizializza il client Telegram
client = TelegramClient('monitor_session', api_id, api_hash)

# Variabili per tracciare lo stato dei gruppi
tracked_groups = {}  # {group_link: {"status": "active/banned/deleted", "time": datetime}}

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

# Funzione per monitorare i gruppi
async def monitor_group(group_link):
    group_id = group_link.split("/")[-1]  # Ricava l'ID del gruppo dal link
    tracked_groups[group_link] = {"status": "pending", "time": datetime.now()}

    try:
        # Verifica che il gruppo esista ancora
        await client.get_entity(group_id)
        tracked_groups[group_link]["status"] = "active"
        return False
    except Exception:
        # Il gruppo è bannato/eliminato
        tracked_groups[group_link]["status"] = "banned"
        return True

# Comando: /report
@client.on(events.NewMessage(pattern=r'/report (.+)'))
async def report_handler(event):
    group_link = event.pattern_match.group(1)
    await event.reply(f"Tracking the group: {group_link}. Please wait...")

    # Analizza il gruppo e genera il messaggio
    banned = await monitor_group(group_link)

    if banned:
        await event.reply(f"The group {group_link} has been banned or deleted.")
        send_email(
            to_email="support@telegram.org",
            subject="Group Violation Report",
            body=f"The group {group_link} has been banned or deleted."
        )
    else:
        await event.reply(f"The group {group_link} is active and being monitored.")
        send_email(
            to_email="support@telegram.org",
            subject="Group Status Report",
            body=f"The group {group_link} is active and being monitored."
        )

# Comando: /lista
@client.on(events.NewMessage(pattern=r'/lista'))
async def list_handler(event):
    message = "Tracked Groups:\n"
    for group, data in tracked_groups.items():
        status = data["status"]
        time_tracked = data["time"].strftime("%Y-%m-%d %H:%M:%S")
        message += f"- {group}: {status} (since {time_tracked})\n"
    await event.reply(message)

# Task periodico: controlla lo stato dei gruppi
async def check_tracked_groups():
    while True:
        for group_link, data in list(tracked_groups.items()):
            if data["status"] == "banned":
                continue

            group_id = group_link.split("/")[-1]

            try:
                await client.get_entity(group_id)
            except Exception:
                # Il gruppo è stato eliminato o bannato
                tracked_groups[group_link]["status"] = "deleted"
                await client.send_message(
                    AUTHORIZED_GROUP_ID,
                    f"The group {group_link} has been deleted or banned."
                )
        await asyncio.sleep(3600)  # Controlla ogni ora

# Funzione principale
async def main():
    print("Bot attivo e in ascolto...")
    await client.start()
    client.loop.create_task(check_tracked_groups())

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main())
