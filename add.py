from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneNumberInvalidError
import os

# Credenziali API Telegram
api_id = 25373607  # Inserisci il tuo API ID
api_hash = '3b559c2461a210c9654399b66125bc0b'  # Inserisci il tuo API Hash

# Assicurati che la cartella per le sessioni esista
if not os.path.exists('sessions'):
    os.makedirs('sessions')

def add_account(phone_number):
    try:
        client = TelegramClient(f'sessions/{phone_number}', api_id, api_hash)
        client.connect()

        if not client.is_user_authorized():
            try:
                # Richiede il codice OTP inviato via Telegram
                client.send_code_request(phone_number)
                code = input(f"Inserisci il codice ricevuto per {phone_number}: ").strip()
                client.sign_in(phone_number, code)
            except PhoneCodeInvalidError:
                print("Codice OTP non valido. Riprova.")
                return
            except SessionPasswordNeededError:
                password = input(f"Inserisci la password per {phone_number}: ").strip()
                client.sign_in(password=password)
            except PhoneNumberInvalidError:
                print("Numero di telefono non valido. Riprova.")
                return

        # Conferma che il login è avvenuto con successo
        me = client.get_me()
        print(f"Accesso riuscito come {me.first_name} ({phone_number})")

    except Exception as e:
        print(f"Errore durante il login: {e}")
    finally:
        # Chiudi la connessione
        client.disconnect()

if __name__ == '__main__':
    phone_number = input("Inserisci il numero di telefono con prefisso internazionale (es. +39...): ").strip()
    if phone_number:
        add_account(phone_number)
    else:
        print("Nessun numero di telefono fornito.")
