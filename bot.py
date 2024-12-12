import os
import asyncio
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import ChannelInvalidError

# Configurazione API Telegram (direttamente nello script)
api_id = 25373607
api_hash = "3b559c2461a210c9654399b66125bc0b"
bot_token = "7659684235:AAG7TOMLBRpd7pgNybU0UOrAucvxTANC9H0"  # Inserisci il token del bot qui
AUTHORIZED_USER_ID = 6849853752

# Configurazione SMTP per email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "abadaalessandro6@gmail.com"
EMAIL_PASSWORD = "tult pukz jfle txfr"

# Token Hugging Face
HF_TOKEN = "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"
HF_GENERATION_URL = "https://api-inference.huggingface.co/models/gpt2"

# Inizializza il client Telegram come bot
client = TelegramClient("bot", api_id, api_hash).start(bot_token=bot_token)

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

# Comando: /start
@client.on(events.NewMessage(pattern=r"/start"))
async def start_handler(event):
    if event.sender_id == AUTHORIZED_USER_ID:
        await event.reply(
            "Ciao! Sono attivo. Usa /report <username> per monitorare un gruppo e /lista per visualizzare i gruppi monitorati."
        )
    else:
        await event.reply("Non sei autorizzato a utilizzare questo bot.")

# Comando: /report <username>
@client.on(events.NewMessage(pattern=r"/report (.+)"))
async def report_handler(event):
    if event.sender_id != AUTHORIZED_USER_ID:
        return

    group_username = event.pattern_match.group(1).strip()
    await event.reply(f"Analizzando il gruppo @{group_username}...")

    try:
        # Verifica se il bot è nel gruppo
        group = await client.get_entity(group_username)
    except Exception:
        await event.reply(f"Gruppo @{group_username} non trovato o inaccessibile.")
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
        await event.reply(f"Gruppo @{group_username} segnalato e ora monitorato.")
    else:
        await event.reply(f"Gruppo @{group_username} è già monitorato.")

# Comando: /lista
@client.on(events.NewMessage(pattern=r"/lista"))
async def list_handler(event):
    if event.sender_id != AUTHORIZED_USER_ID:
        return

    if not tracked_groups:
        await event.reply("Nessun gruppo è attualmente monitorato.")
        return

    message = "Gruppi monitorati:\n"
    for group, data in tracked_groups.items():
        status = data["status"]
        last_check = data["last_check"].strftime("%Y-%m-%d %H:%M:%S")
        reported_at = data["reported_at"].strftime("%Y-%m-%d %H:%M:%S")
        message += f"- @{group}: {status} (Ultimo controllo: {last_check}, Segnalato: {reported_at})\n"

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
                        f"Gruppo @{group} è stato bannato o eliminato. Segnalazione riuscita!",
                    )
                elif status == "active":
                    await client.send_message(
                        AUTHORIZED_USER_ID,
                        f"Gruppo @{group} è stato riattivato. Segnalazione non riuscita!",
                    )
            # Notifica se il gruppo non è stato bannato entro 2 settimane
            elif last_status == "active" and (now - data["reported_at"]) > timedelta(weeks=2):
                await client.send_message(
                    AUTHORIZED_USER_ID,
                    f"Gruppo @{group} non è stato bannato dopo 2 settimane. Segnalazione fallita."
                )
                del tracked_groups[group]  # Rimuove il gruppo dalla lista

        await asyncio.sleep(3600)  # Controlla ogni ora

# Funzione principale
async def main():
    print("Bot avviato e in ascolto...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
