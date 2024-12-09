from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
import os

api_id = 25373607
api_hash = '3b559c2461a210c9654399b66125bc0b

def add_account(phone_number):
    client = TelegramClient(f'sessions/{phone_number}', api_id, api_hash)
    client.connect()

    if not client.is_user_authorized():
        try:
            client.send_code_request(phone_number)
            code = input(f"Inserisci il codice ricevuto via Telegram per {phone_number}: ")
            client.sign_in(phone_number, code)
        except SessionPasswordNeededError:
            password = input(f"Inserisci la tua password per {phone_number}: ")
            client.sign_in(password=password)

    print(f"Account {phone_number} aggiunto con successo!")
    client.disconnect()

if __name__ == '__main__':
    phone_number = input('Inserisci il numero di telefono con prefisso internazionale (es. +39...): ')
    add_account(phone_number)
