from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import UserPrivacyRestrictedError, ChannelInvalidError
from datetime import datetime, timedelta
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
import pickle

# Configurazione API Telegram
api_id = 21963510
api_hash = "eddfccf6e4ea21255498028e5af25eb1"
AUTHORIZED_USER_ID = 6849853752  # ID dell'utente autorizzato

# Configurazione SMTP per email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "abadaalessandro6@gmail.com"
EMAIL_PASSWORD = "tult pukz jfle txfr"

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

# Funzione per verificare se il gruppo è stato bannato o eliminato
async def check_group_status(group_username, client):
    try:
        await client.get_entity(group_username)
        return "active"  # Gruppo ancora attivo
    except ChannelInvalidError:
        return "banned"  # Gruppo bannato o eliminato
    except Exception:
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
async def start_handler(event):
    if event.sender_id == AUTHORIZED_USER_ID:
        await event.reply(
            "Hello! I am active. Use /report <username> to monitor a group and /lista to view the monitored groups."
        )
    else:
        await event.reply("You are not authorized to use this bot.")

# Comando: /report <username>
async def report_handler(event, clients):
    if event.sender_id != AUTHORIZED_USER_ID:
        return

    group_username = event.pattern_match.group(1).strip()
    await event.reply(f"Analyzing group @{group_username}...")

    for client in clients:
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
            email_body = create_email_report(group_username)
            send_email(
                to_email="support@telegram.org",
                subject=f"Group Report: @{group_username}",
                body=email_body,
            )
            await event.reply(f"Group @{group_username} has been reported and is now being monitored.")
        else:
            await event.reply(f"Group @{group_username} is already being monitored.")

# Funzione per monitorare i gruppi segnalati
async def monitor_groups(clients):
    while True:
        now = datetime.now()
        for group, data in list(tracked_groups.items()):
            # Controlla lo stato del gruppo
            status = await check_group_status(group, clients[0])  # Usa il primo client per monitorare
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
    
    # Carica le sessioni create tramite add.py
    session_files = os.listdir('sessions/')
    clients = []
    
    for session_file in session_files:
        client = TelegramClient(f'sessions/{session_file}', api_id, api_hash)
        clients.append(client)

    # Avvia tutti i client Telegram
    for client in clients:
        await client.start()

    # Monitoraggio dei gruppi
    client.loop.create_task(monitor_groups(clients))
    
    # Esegui il bot fino alla disconnessione
    await client.run_until_disconnected()

if __name__ == "__main__":
    with TelegramClient("userbot", api_id, api_hash) as client:
        client.loop.run_until_complete(main())
