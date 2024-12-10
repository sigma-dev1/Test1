import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import UserPrivacyRestrictedError
import tensorflow as tf
from transformers import TFAutoModelForSequenceClassification, AutoTokenizer
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

# ID utente autorizzato
AUTHORIZED_USER_ID = 6849853752  # Cambia con l'ID dell'utente autorizzato

# Variabili per tracciare lo stato dei gruppi
tracked_groups = {}  # {group_link: {"status": "active/banned/deleted", "last_check": datetime}}

# Inizializza il modello di intelligenza artificiale e il tokenizer
print("Caricamento del tokenizer e del modello...")
tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased-finetuned-sst-2-english")
model = TFAutoModelForSequenceClassification.from_pretrained("distilbert-base-uncased-finetuned-sst-2-english")
print("Tokenizer e modello caricati.")

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

# Inizializza il client Telegram
client = TelegramClient("bot", api_id, api_hash).start(bot_token=bot_token)
print("Client Telegram inizializzato.")

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

    inputs = tokenizer(content, return_tensors="tf")
    outputs = model(inputs)
    scores = outputs[0][0].numpy()
    predictions = tf.nn.softmax(scores).numpy()
    labels = ["NEGATIVE", "POSITIVE"]
    analysis = [{"label": labels[i], "score": predictions[i]} for i in range(len(labels))]
    print("Analisi completata.")

    return analysis

# Funzione per creare una segnalazione email basata sull'analisi dell'IA
def create_report(group_link, analysis):
    violations = [item for item in analysis if item['label'] == 'NEGATIVE' and item['score'] > 0.6]  # Soglia di confidenza
    if violations:
        violation_details = "\n".join([f"Text: {item['label']} | Confidence: {item['score']}" for item in violations])
        report = (
            f"Dear Telegram Support,\n\n"
            f"I would like to report the following group: {group_link}.\n\n"
            f"This group appears to violate Telegram's Terms of Service based on the following content:\n\n"
            f"{violation_details}\n\n"
            f"Thank you for your prompt attention to this matter.\n\n"
            f"Best regards,\nA concerned user"
        )
    else:
        report = (
            f"Dear Telegram Support,\n\n"
            f"I would like to report the following group: {group_link}.\n\n"
            f"No specific violations were found, but please review the group for compliance with Telegram's Terms of Service.\n\n"
            f"Thank you for your prompt attention to this matter.\n\n"
            f"Best regards,\nA concerned user"
        )
    print("Report creato.")
    return report

# Funzione per inviare notifiche di tracciamento
async def send_tracking_notifications():
    while True:
        for group_link, data in list(tracked_groups.items()):
            group_id = group_link.split("/")[-1]
            try:
                await client.get_entity(group_id)
                if data["status"] in ["banned", "deleted"]:
                    tracked_groups[group_link]["status"] = "active"
                    await client.send_message(
                        AUTHORIZED_USER_ID,
                        f"The group {group_link} is now active again.",
                    )
            except UserPrivacyRestrictedError:
                if data["status"] == "active":
                    tracked_groups[group_link]["status"] = "deleted"
                    await client.send_message(
                        AUTHORIZED_USER_ID,
                        f"The group {group_link} has been deleted or banned.",
                    )
            await asyncio.sleep(10)  # Controlla ogni 10 secondi per dimostrazione

# Comando: /start
@client.on(events.NewMessage(pattern=r"/start"))
async def start_handler(event):
    if event.sender_id == AUTHORIZED_USER_ID:
        await event.reply("Ciao, sto funzionando! Utilizza i comandi /report e /lista per monitorare e analizzare i gruppi.")
        print("Messaggio di avvio inviato all'utente autorizzato.")

# Comando: /report
@client.on(events.NewMessage(pattern=r"/report (.+)"))
async def report_handler(event):
    if event.sender_id != AUTHORIZED_USER_ID:
        return

    group_link = event.pattern_match.group(1)
    await event.reply(f"Monitoring the group: {group_link}. Please wait...")

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
        await event.reply(f"The group {group_link} is already banned. Report submitted.\n\n{email_preview}")
    else:
        await event.reply(
            f"Report submitted for the group {group_link}. It will be continuously monitored.\n\n{email_preview}"
        )

# Comando: /lista
@client.on(events.NewMessage(pattern=r"/lista"))
async def list_handler(event):
    if event.sender_id != AUTHORIZED_USER_ID:
        return

    message = "Tracked Groups:\n"
    for group, data in tracked_groups.items():
        status = data["status"]
        last_check = data["last_check"].strftime("%Y-%m-%d %H:%M:%S")
        message += f"- {group}: {status} (Last checked: {last_check})\n"

    await event.reply(message)

# Funzione principale
async def main():
    print("Bot is active and listening...")
    await client.start()
    client.loop.create_task(send_tracking_notifications())

if __name__ == "__main__":
    # Avvia il client Telegram
    with client:
        # Il bot rimarrà attivo finché il client è attivo
        client.loop.run_until_complete(main())
