import os
import asyncio
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import ChannelInvalidError

# Configurazione API Telegram
api_id = 25373607
api_hash = "3b559c2461a210c9654399b66125bc0b"
bot_token = "7659684235:AAG7TOMLBRpd7pgNybU0UOrAucvxTANC9H0"
AUTHORIZED_USER_ID = 6849853752

# Configurazione SMTP per email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "abadaalessandro6@gmail.com"
EMAIL_PASSWORD = "tult pukz jfle txfr"

# Token OpenAI
OPENAI_API_KEY = "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"

# Inizializza il client Telegram come bot
client = TelegramClient("bot", api_id, api_hash).start(bot_token=bot_token)

# Stato dei gruppi monitorati
tracked_groups = {}
pending_details = {}  # Memorizza i gruppi in attesa di dettagli

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
        print(f"Email successfully sent to {to_email}.")
        return f"Subject: {subject}\n\n{body}"
    except Exception as e:
        print(f"Error while sending email: {e}")
        return "Error while sending email."

# Funzione per generare il testo tramite OpenAI
def generate_report_text(group_username, details):
    prompt = f"Generate a professional email report about the group @{group_username}. Details: {details}. The report should highlight how the group violates Telegram's Terms of Service and request its banning."
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }
    payload = {
        "model": "text-davinci-003",
        "prompt": prompt,
        "max_tokens": 500,
        "temperature": 0.7,
    }

    try:
        response = requests.post("https://api.openai.com/v1/completions", headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["choices"][0]["text"].strip()
        else:
            print(f"Error generating text: {response.text}")
            return "Error generating report."
    except Exception as e:
        print(f"Error connecting to OpenAI: {e}")
        return "Error generating report."

# Comando: /start
@client.on(events.NewMessage(pattern=r"/start"))
async def start_handler(event):
    if event.sender_id == AUTHORIZED_USER_ID:
        await event.reply("Hello! I'm active. Use /report <username> to monitor a group, /skip to skip details, and /list to see monitored groups.")
    else:
        await event.reply("You are not authorized to use this bot.")

# Comando: /report <username>
@client.on(events.NewMessage(pattern=r"/report (.+)"))
async def report_handler(event):
    if event.sender_id != AUTHORIZED_USER_ID:
        return

    group_username = event.pattern_match.group(1).strip()
    await event.reply(f"Analyzing the group @{group_username}...")

    try:
        group = await client.get_entity(group_username)
    except Exception:
        await event.reply(f"Group @{group_username} not found or inaccessible.")
        return

    if group_username not in tracked_groups:
        tracked_groups[group_username] = {
            "status": "active",
            "last_check": datetime.now(),
            "reported_at": None,
        }
        pending_details[group_username] = True
        await event.reply(
            f"Please provide details about why the group @{group_username} should be reported. Use /skip to skip this step."
        )
    else:
        await event.reply(f"The group @{group_username} is already being monitored.")

# Comando: /skip
@client.on(events.NewMessage(pattern=r"/skip"))
async def skip_handler(event):
    if event.sender_id != AUTHORIZED_USER_ID:
        return

    for group_username in list(pending_details.keys()):
        details = "No additional details provided."
        email_body = generate_report_text(group_username, details)
        email_content = send_email(
            to_email="support@telegram.org",
            subject=f"Group Report: @{group_username}",
            body=email_body,
        )
        tracked_groups[group_username]["reported_at"] = datetime.now()
        del pending_details[group_username]

        await event.reply(
            f"The group @{group_username} has been reported successfully. Here is the email sent:\n\n{email_content}"
        )

# Comando: /list
@client.on(events.NewMessage(pattern=r"/list"))
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
        reported_at = (
            data["reported_at"].strftime("%Y-%m-%d %H:%M:%S")
            if data["reported_at"]
            else "Not reported yet"
        )
        message += f"- @{group}: {status} (Last check: {last_check}, Reported: {reported_at})\n"

    await event.reply(message)

# Funzione principale
async def main():
    print("Bot is up and running...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
