import os
import asyncio
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import ChannelInvalidError
from telethon.errors import SessionPasswordNeededError

# Gestione sicura delle configurazioni tramite variabili d'ambiente
import os
from dotenv import load_dotenv

# Carica le variabili d'ambiente
load_dotenv()

# Configurazione API Telegram
api_id = os.getenv('TELEGRAM_API_ID', '25373607')
api_hash = os.getenv('TELEGRAM_API_HASH', '3b559c2461a210c9654399b66125bc0b')
AUTHORIZED_USER_ID = int(os.getenv('AUTHORIZED_USER_ID', '6849853752'))

# Configurazione SMTP per email
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', 'abadaalessandro6@gmail.com')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'tult pukz jfle txfr')

# Token Hugging Face
HF_TOKEN = os.getenv('HF_TOKEN', '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')
HF_GENERATION_URL = os.getenv('HF_GENERATION_URL', 'https://api-inference.huggingface.co/models/gpt2')

# Inizializza il client Telegram
client = TelegramClient("userbot", api_id, api_hash)

# Stato dei gruppi monitorati
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
        print(f"Errore durante l'invio dell'email: {e}")

# Funzione per generare un testo professionale per la segnalazione
def generate_report_text(group_username):
    prompt = f"Please generate a professional email report about the group @{group_username} which violates Telegram's Terms of Service. Include necessary details to request banning of the group."

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
    }

    try:
        response = requests.post(HF_GENERATION_URL, headers=headers, json={"inputs": prompt})

        if response.status_code == 200:
            return response.json()[0]["generated_text"]
        else:
            print("Error generating text:", response.text)
            return "Error generating report."
    except Exception as e:
        print(f"Errore nella generazione del testo: {e}")
        return "Impossibile generare il report."

# Funzione per verificare se il gruppo è stato bannato o eliminato
async def check_group_status(group_username):
    try:
        await client.get_entity(group_username)
        return "active"  # Gruppo ancora attivo
    except ChannelInvalidError:
        return "banned"  # Gruppo bannato o eliminato
    except Exception as e:
        print(f"Errore nella verifica dello stato del gruppo: {e}")
        return "unknown"  # Altro errore

# Funzione per creare la segnalazione email
def create_email_report(group_username):
    report = (
        f"Dear Telegram Support,\n\n"
        f"I would like to report the group @{group_username} for violating Telegram's Terms of Service. "
        f"Please review the content and take appropriate action.\n\n"
        f"Thank you for your attention.\n\n"
        f"Best regards,\nA concerned user"
    )
    return report

# Comando: /start
@client.on(events.NewMessage(pattern=r"/start"))
async def start_handler(event):
    if event.sender_id == AUTHORIZED_USER_ID:
        await event.reply(
            "Hello! I am active. Use /report <username> to monitor a group and /lista to view the monitored groups."
        )
    else:
        await event.reply("You are not authorized to use this bot.")

# Comando: /report <username>
@client.on(events.NewMessage(pattern=r"/report (.+)"))
async def report_handler(event):
    if event.sender_id != AUTHORIZED_USER_ID:
        return

    group_username = event.pattern_match.group(1).strip()
    await event.reply(f"Analyzing group @{group_username}...")

    try:
        # Verifica se il bot è nel gruppo
        group = await client.get_entity(group_username)
    except Exception:
        await event.reply(f"Group @{group_username} not found or inaccessible.")
        return

    # Aggiorna o aggiungi il gruppo alla lista monitorata
    if group_username not in tracked_groups:
        tracked_groups[group_username] = {
            "status": "active",
            "last_check": datetime.now(),
            "reported_at": datetime.now(),
        }
        
        # Genera il testo per la segnalazione
        email_body = generate_report_text(group_username)
        send_email(
            to_email="support@telegram.org",
            subject=f"Group Report: @{group_username}",
            body=email_body,
        )
        await event.reply(f"Group @{group_username} has been reported and is now being monitored.")
    else:
        await event.reply(f"Group @{group_username} is already being monitored.")

# Comando: /lista
@client.on(events.NewMessage(pattern=r"/lista"))
async def list_handler(event):
    if event.sender_id != AUTHORIZED_USER_ID:
        return

    if not tracked_groups:
        await event.reply("No groups are currently being monitored.")
        return

    message = "Monitored groups:\n"
    for group, data in tracked_groups.items():
        status = data["status"]
        last_check = data["last_check"].strftime("%Y-%m-%d %H:%M:%S")
        reported_at = data["reported_at"].strftime("%Y-%m-%d %H:%M:%S")
        message += f"- @{group}: {status} (Last check: {last_check}, Reported: {reported_at})\n"

    await event.reply(message)

# Funzione per monitorare i gruppi segnalati
async def monitor_groups():
    while True:
        now = datetime.now()
        for group, data in list(tracked_groups.items()):
            # Controlla lo stato del gruppo
            status = await check_group_status(group)
            last_status = data["status"]

            # Aggiorna lo stato se è cambiato
            if status != last_status:
                tracked_groups[group]["status"] = status
                tracked_groups[group]["last_check"] = now

                # Invia notifica all'utente
                if status == "banned":
                    await client.send_message(
                        AUTHORIZED_USER_ID,
                        f"Group @{group} has been banned or deleted. Report successful!",
                    )
                elif status == "active":
                    await client.send_message(
                        AUTHORIZED_USER_ID,
                        f"Group @{group} has been reactivated. Report unsuccessful!",
                    )
            # Notifica se il gruppo non è stato bannato entro 2 settimane
            elif last_status == "active" and (now - data["reported_at"]) > timedelta(weeks=2):
                await client.send_message(
                    AUTHORIZED_USER_ID,
                    f"Group @{group} has not been banned after 2 weeks. Report failed."
                )
                del tracked_groups[group]  # Rimuove il gruppo dalla lista

        await asyncio.sleep(3600)  # Controlla ogni ora

# Funzione principale
async def main():
    print("Userbot attivo e in ascolto...")
    await client.start()
    client.loop.create_task(monitor_groups())
    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
