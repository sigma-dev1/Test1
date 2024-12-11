import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import UserPrivacyRestrictedError, ChannelInvalidError

# Configurazione API Telegram
api_id = 25373607
api_hash = "3b559c2461a210c9654399b66125bc0b"
AUTHORIZED_USER_ID = 6849853752  # ID dell'utente autorizzato

# Configurazione SMTP per email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "abadaalessandro6@gmail.com"
EMAIL_PASSWORD = "tult pukz jfle txfr"

# Token Hugging Face
HF_TOKEN = "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"
HF_GENERATION_URL = "https://api-inference.huggingface.co/models/gpt-3.5-turbo"

# Inizializza il client Telegram
client = TelegramClient("userbot", api_id, api_hash)

# Stato dei gruppi monitorati
tracked_groups = {}  # {group_username: {"status": "active/banned", "last_check": datetime, "reported_at": datetime}}

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

# Funzione per generare una segnalazione con Hugging Face
def generate_email_content(group_username, analysis_summary):
    prompt = (
        f"Write a formal email to Telegram Support reporting the group @{group_username}. "
        f"The group violates Telegram's policies. Here is the analysis summary:\n{analysis_summary}\n\n"
        f"Write a professional and concise report."
    )
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": prompt, "parameters": {"max_length": 300}}
    response = requests.post(HF_GENERATION_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json().get("generated_text", "Error generating email content.")
    else:
        return "Error: Unable to generate email content."

# Funzione per analizzare i messaggi da un file
def analyze_text(file_path):
    try:
        with open(file_path, "r") as file:
            text = file.read()
        prompt = (
            f"Analyze the following group chat messages for harmful content. Summarize the violations and behaviors found:\n{text}"
        )
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        payload = {"inputs": prompt, "parameters": {"max_length": 300}}
        response = requests.post(HF_GENERATION_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json().get("generated_text", "Error analyzing text.")
        else:
            return "Error: Unable to analyze text."
    except Exception as e:
        return f"Errore durante l'analisi del file: {e}"

# Comando: /start
@client.on(events.NewMessage(pattern=r"/start"))
async def start_handler(event):
    if event.sender_id == AUTHORIZED_USER_ID:
        await event.reply("Userbot attivo! Usa /report <username> per segnalare un gruppo o /lista per vedere i gruppi monitorati.")
    else:
        await event.reply("Non sei autorizzato a usare questo bot.")

# Comando: /report <username>
@client.on(events.NewMessage(pattern=r"/report (.+)"))
async def report_handler(event):
    if event.sender_id != AUTHORIZED_USER_ID:
        return

    group_username = event.pattern_match.group(1).strip()
    await event.reply(f"Inserisci il file .txt dei messaggi per analizzare il gruppo @{group_username}.")
    tracked_groups[group_username] = {"status": "active", "reported_at": datetime.now(), "last_check": datetime.now()}

# Gestione dei file caricati per analisi
@client.on(events.NewMessage)
async def file_handler(event):
    if event.sender_id == AUTHORIZED_USER_ID and event.file:
        file_path = await event.download_media()
        group_username = list(tracked_groups.keys())[-1]
        analysis_summary = analyze_text(file_path)
        email_body = generate_email_content(group_username, analysis_summary)
        send_email("support@telegram.org", f"Report for @{group_username}", email_body)
        await event.reply(f"Analisi completata e segnalazione inviata per @{group_username}.")
        os.remove(file_path)

# Comando: /lista
@client.on(events.NewMessage(pattern=r"/lista"))
async def list_handler(event):
    if event.sender_id != AUTHORIZED_USER_ID:
        return

    if not tracked_groups:
        await event.reply("Nessun gruppo monitorato al momento.")
    else:
        message = "Gruppi monitorati:\n"
        for group, data in tracked_groups.items():
            status = data["status"]
            last_check = data["last_check"].strftime("%Y-%m-%d %H:%M:%S")
            reported_at = data["reported_at"].strftime("%Y-%m-%d %H:%M:%S")
            message += f"- @{group}: {status} (Ultimo controllo: {last_check}, Segnalato: {reported_at})\n"
        await event.reply(message)

# Avvia il bot
async def main():
    print("Userbot avviato.")
    await client.start()
    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
