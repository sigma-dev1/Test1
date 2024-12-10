import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import UserPrivacyRestrictedError
import os
import asyncio
from datetime import datetime

# Credenziali API Telegram
api_id = 25373607
api_hash = "3b559c2461a210c9654399b66125bc0b"

# Configurazione SMTP per email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "abadaalessandro6@gmail.com"
EMAIL_PASSWORD = "tult pukz jfle txfr"

# ID utente autorizzato e gruppo log
AUTHORIZED_USER_ID = 6849853752  # Cambia con l'ID dell'utente autorizzato
AUTHORIZED_GROUP_ID = -4692421717  # Cambia con l'ID del gruppo autorizzato

# Percorso della directory delle sessioni
SESSION_DIR = "sessions"

# Variabili per tracciare lo stato dei gruppi
tracked_groups = {}  # {group_link: {"status": "active/banned/deleted", "last_check": datetime}}

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
    except Exception as e:
        print(f"Error sending email: {e}")

# Trova la sessione salvata
def find_session():
    if not os.path.exists(SESSION_DIR):
        print("No saved session found. Please add an account using add.py first.")
        return None
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith(".session")]
    if not sessions:
        print("No saved session found. Please add an account using add.py first.")
        return None
    return os.path.join(SESSION_DIR, sessions[0].replace(".session", ""))

# Trova una sessione valida
session_name = find_session()
if not session_name:
    exit(1)

# Inizializza il client Telegram
client = TelegramClient(session_name, api_id, api_hash)

# Funzione per monitorare un gruppo
async def monitor_group(group_link):
    group_id = group_link.split("/")[-1]
    tracked_groups[group_link] = {"status": "active", "last_check": datetime.now()}

    try:
        # Verifica che il gruppo esista ancora
        await client.get_entity(group_id)
        return False  # Gruppo attivo
    except Exception:
        # Gruppo bannato/eliminato
        tracked_groups[group_link]["status"] = "banned"
        return True  # Gruppo bannato

# Funzione per creare una segnalazione email
def create_report(group_link):
    return (
        f"Dear Telegram Support,\n\n"
        f"I would like to report the following group: {group_link}.\n\n"
        f"This group appears to violate Telegram's Terms of Service, and I kindly request that you review its activities. "
        f"Groups like this often engage in spam, hateful content, or other prohibited activities that harm the community.\n\n"
        f"Thank you for your prompt attention to this matter.\n\n"
        f"Best regards,\nA concerned user"
    )

# Comando: /report
@client.on(events.NewMessage(pattern=r"/report (.+)"))
async def report_handler(event):
    if event.sender_id != AUTHORIZED_USER_ID or event.chat_id != AUTHORIZED_GROUP_ID:
        return

    group_link = event.pattern_match.group(1)
    await event.reply(f"Monitoring the group: {group_link}. Please wait...")

    # Aggiungi il gruppo ai tracciati
    banned = await monitor_group(group_link)
    report_message = create_report(group_link)

    # Invia segnalazione email
    send_email(
        to_email="support@telegram.org",
        subject=f"Group Report: {group_link}",
        body=report_message,
    )

    if banned:
        tracked_groups[group_link]["status"] = "banned"
        await event.reply(f"The group {group_link} is already banned. Report submitted.")
    else:
        await event.reply(
            f"Report submitted for the group {group_link}. It will be continuously monitored."
        )

# Comando: /lista
@client.on(events.NewMessage(pattern=r"/lista"))
async def list_handler(event):
    if event.sender_id != AUTHORIZED_USER_ID or event.chat_id != AUTHORIZED_GROUP_ID:
        return

    message = "Tracked Groups:\n"
    for group, data in tracked_groups.items():
        status = data["status"]
        last_check = data["last_check"].strftime("%Y-%m-%d %H:%M:%S")
        message += f"- {group}: {status} (Last checked: {last_check})\n"

    await event.reply(message)

# Funzione per monitorare continuamente i gruppi
async def monitor_tracked_groups():
    while True:
        for group_link, data in list(tracked_groups.items()):
            if data["status"] in ["banned", "deleted"]:
                continue

            group_id = group_link.split("/")[-1]
            try:
                await client.get_entity(group_id)
            except UserPrivacyRestrictedError:
                tracked_groups[group_link]["status"] = "deleted"
                await client.send_message(
                    AUTHORIZED_GROUP_ID,
                    f"The group {group_link} has been deleted or banned.",
                )
                # Reinvia la segnalazione per assicurarsi che non venga ripristinato
                report_message = create_report(group_link)
                send_email(
                    to_email="support@telegram.org",
                    subject=f"Follow-up Report: {group_link}",
                    body=report_message,
                )
        await asyncio.sleep(3600)  # Controlla ogni ora

# Funzione principale
async def main():
    print("Bot is active and listening...")
    await client.start()
    client.loop.create_task(monitor_tracked_groups())

if __name__ == "__main__":
    # Avvia il client Telegram
    with client:
        # Il bot rimarrà attivo finché il client è attivo
        client.loop.run_until_complete(main())
