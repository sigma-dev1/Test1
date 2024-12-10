import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telethon import TelegramClient, events
from telethon.errors import UserPrivacyRestrictedError, ChatAdminRequiredError
import os
import asyncio
from datetime import datetime
import tensorflow as tf
from transformers import TFAutoModelForSequenceClassification, AutoTokenizer

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

# Carica modello di intelligenza artificiale
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
        print(f"Email inviata con successo a {to_email}.")
    except Exception as e:
        print(f"Errore nell'invio dell'email: {e}")

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

# Funzione per analizzare i messaggi di un gruppo
async def analyze_group_content(group_link):
    try:
        group = await client.get_entity(group_link)
        messages = await client.get_messages(group, limit=100)  # Ultimi 100 messaggi
        content = " ".join([msg.message for msg in messages if msg.message])

        inputs = tokenizer(content, return_tensors="tf")
        outputs = model(inputs)
        scores = outputs.logits.numpy()[0]
        predictions = tf.nn.softmax(scores).numpy()
        labels = ["NEGATIVE", "POSITIVE"]

        analysis = [{"label": labels[i], "score": predictions[i]} for i in range(len(labels))]
        return analysis
    except ChatAdminRequiredError:
        print(f"Accesso negato al gruppo {group_link}.")
        return []
    except Exception as e:
        print(f"Errore durante l'analisi del gruppo {group_link}: {e}")
        return []

# Funzione per creare una segnalazione email
def create_report(group_link, analysis):
    violations = [item for item in analysis if item['label'] == 'NEGATIVE' and item['score'] > 0.6]
    if violations:
        violation_details = "\n".join([f"Label: {item['label']} | Confidence: {item['score']:.2f}" for item in violations])
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
    return report

# Comando: /start
@client.on(events.NewMessage(pattern=r"/start"))
async def start_handler(event):
    if event.sender_id == AUTHORIZED_USER_ID:
        await event.reply("Ciao! Usa /report [link gruppo] per monitorare e analizzare un gruppo. Usa /lista per vedere i gruppi monitorati.")
        print("Messaggio di avvio inviato.")

# Comando: /report
@client.on(events.NewMessage(pattern=r"/report (.+)"))
async def report_handler(event):
    if event.sender_id != AUTHORIZED_USER_ID:
        return

    group_link = event.pattern_match.group(1)
    await event.reply(f"Monitoraggio del gruppo {group_link}. Attendi...")

    banned = await monitor_group(group_link)
    analysis = await analyze_group_content(group_link)
    report_message = create_report(group_link, analysis)

    send_email(
        to_email="support@telegram.org",
        subject=f"Group Report: {group_link}",
        body=report_message,
    )

    if banned:
        await event.reply(f"Il gruppo {group_link} è bannato. Segnalazione inviata.")
    else:
        await event.reply(f"Segnalazione inviata per il gruppo {group_link}. Continuerà a essere monitorato.")

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
    print("Bot in esecuzione...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    client.loop.run_until_complete(main())
