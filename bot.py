import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
import requests
import asyncio
from datetime import datetime

# Credenziali API di Telegram
api_id = 21963510  # Inserisci il tuo API ID
api_hash = 'eddfccf6e4ea21255498028e5af25eb1'  # Inserisci il tuo API Hash

# Configurazione SMTP per email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "abadaalessandro6@gmail.com"  # Email che invia le segnalazioni
EMAIL_PASSWORD = "tult pukz jfle txfr"  # Password o password per app

# API gratuita per generazione di testo intelligente
AI_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
headers = {"Authorization": "Bearer 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"}  # Inserisci un token valido o usane uno gratuito

# ID utente autorizzato e gruppo log
AUTHORIZED_USER_ID = 6849853752
AUTHORIZED_GROUP_ID = -4692421717

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

# Funzione per generare un messaggio dettagliato tramite AI
def generate_ai_message(group_link):
    prompt = f"Generate a formal and persuasive email to Telegram Support about the group {group_link}. The email should explain why the group violates Telegram's terms of service, including examples of prohibited content like hate speech, spam, or illegal activities."
    try:
        response = requests.post(AI_API_URL, headers=headers, json={"inputs": prompt})
        if response.status_code == 200:
            return response.json()["generated_text"]
        else:
            print("Errore nella richiesta all'API AI.")
            return f"The group {group_link} violates Telegram's policies by sharing prohibited content."
    except Exception as e:
        print(f"Errore durante la generazione del messaggio: {e}")
        return f"The group {group_link} violates Telegram's policies by sharing prohibited content."

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
    if event.chat_id != AUTHORIZED_GROUP_ID or event.sender_id != AUTHORIZED_USER_ID:
        await event.reply("You are not authorized to use this bot.")
        return

    group_link = event.pattern_match.group(1)
    await event.reply(f"Tracking the group: {group_link}. Please wait...")

    # Analizza il gruppo e genera il messaggio
    banned = await monitor_group(group_link)
    ai_message = generate_ai_message(group_link)

    if banned:
        await event.reply(f"The group {group_link} has been banned or deleted.")
        send_email(
            to_email="support@telegram.org",
            subject="Group Violation Report",
            body=ai_message,
        )
    else:
        await event.reply(f"The group {group_link} is being monitored for violations.")
        send_email(
            to_email="support@telegram.org",
            subject="Group Violation Report",
            body=ai_message,
        )

# Comando: /lista
@client.on(events.NewMessage(pattern=r'/lista'))
async def list_handler(event):
    if event.chat_id != AUTHORIZED_GROUP_ID or event.sender_id != AUTHORIZED_USER_ID:
        await event.reply("You are not authorized to use this bot.")
        return

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
                    f"The group {group_link} has been deleted or banned.",
                )
                ai_message = generate_ai_message(group_link)
                send_email(
                    to_email="support@telegram.org",
                    subject="Group Status Update",
                    body=ai_message,
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
