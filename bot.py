import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import UserPrivacyRestrictedError
import openai
import os
import asyncio
from datetime import datetime

# Credenziali API Telegram
api_id = 25373607
api_hash = "3b559c2461a210c9654399b66125bc0b"
bot_token = "7396062831:AAFVJ50ZvxuwUlc2D9Pssj_aWAEd8FquG8Y"

# Configurazione SMTP per email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "abadaalessandro6@gmail.com"
EMAIL_PASSWORD = "tult pukz jfle txfr"

# OpenAI API Key
openai.api_key = "LA_TUA_API_KEY_OPENAI"

# ID utente autorizzato
AUTHORIZED_USER_ID = 6849853752  # Cambia con l'ID dell'utente autorizzato

# Variabili per tracciare lo stato dei gruppi
tracked_groups = {}  # {group_link: {"status": "active/banned/deleted", "last_check": datetime}}

# Inizializza il client Telegram
client = TelegramClient("bot", api_id, api_hash).start(bot_token=bot_token)
print("Client Telegram inizializzato.")

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

# Funzione per analizzare il contenuto con OpenAI
def analyze_content_with_openai(content: str) -> str:
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Analizza il seguente contenuto per eventuali violazioni delle regole:\n{content}",
            max_tokens=200,
            temperature=0.5,
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"Errore nell'analisi con OpenAI: {e}")
        return "Errore durante l'analisi del contenuto."

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

# Funzione per analizzare i messaggi del gruppo
async def analyze_group_content(group_link):
    print(f"Analizzando il contenuto del gruppo: {group_link}")
    group = await client.get_entity(group_link)
    messages = await client.get_messages(group, limit=100)  # Analizza gli ultimi 100 messaggi
    content = " ".join([msg.message for msg in messages if msg.message])

    print("Inizio analisi con OpenAI...")
    analysis = analyze_content_with_openai(content)
    print("Analisi completata.")
    return analysis

# Funzione per creare una segnalazione email
def create_report(group_link, analysis):
    report = (
        f"Dear Telegram Support,\n\n"
        f"I would like to report the following group: {group_link}.\n\n"
        f"This group appears to violate Telegram's Terms of Service based on the following analysis:\n\n"
        f"{analysis}\n\n"
        f"Thank you for your prompt attention to this matter.\n\n"
        f"Best regards,\nA concerned user"
    )
    print("Report creato.")
    return report

# Comando: /start
@client.on(events.NewMessage(pattern=r"/start"))
async def start_handler(event):
    if event.sender_id == AUTHORIZED_USER_ID:
        await event.reply("Ciao, sono attivo! Utilizza i comandi /report e /lista per monitorare e analizzare i gruppi.")
        print("Messaggio di avvio inviato all'utente autorizzato.")

# Comando: /report
@client.on(events.NewMessage(pattern=r"/report (.+)"))
async def report_handler(event):
    if event.sender_id != AUTHORIZED_USER_ID:
        return

    group_link = event.pattern_match.group(1)
    await event.reply(f"Sto monitorando il gruppo: {group_link}. Attendi per favore...")

    # Aggiungi il gruppo ai tracciati
    banned = await monitor_group(group_link)

    # Analizza il contenuto del gruppo
    analysis = await analyze_group_content(group_link)
    report_message = create_report(group_link, analysis)

    # Invia segnalazione email
    send_email(
        to_email="support@telegram.org",
        subject=f"Group Report: {group_link}",
        body=report_message,
    )

    email_preview = (
        f"Email inviata a support@telegram.org:\n\n"
        f"Soggetto: Group Report: {group_link}\n\n"
        f"Corpo del messaggio:\n{report_message}"
    )

    if banned:
        tracked_groups[group_link]["status"] = "banned"
        await event.reply(f"Il gruppo {group_link} è già bannato. Report inviato.\n\n{email_preview}")
    else:
        await event.reply(
            f"Report inviato per il gruppo {group_link}. Continuerà a essere monitorato.\n\n{email_preview}"
        )

# Comando: /lista
@client.on(events.NewMessage(pattern=r"/lista"))
async def list_handler(event):
    if event.sender_id != AUTHORIZED_USER_ID:
        return

    message = "Gruppi monitorati:\n"
    for group, data in tracked_groups.items():
        status = data["status"]
        last_check = data["last_check"].strftime("%Y-%m-%d %H:%M:%S")
        message += f"- {group}: {status} (Ultimo controllo: {last_check})\n"

    await event.reply(message)

# Funzione principale
async def main():
    print("Bot attivo e in ascolto...")
    await client.start()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
