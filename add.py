from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
import pickle
import os

# API credentials
api_id = '21963510'
api_hash = 'eddfccf6e4ea21255498028e5af25eb1'

# Directory per le sessioni
sessions_dir = 'sessions'

# Assicurati che la cartella per le sessioni esista
if not os.path.exists(sessions_dir):
    os.makedirs(sessions_dir)

# File per salvare i numeri di telefono
vars_file = 'vars.txt'

# Crea il file vars.txt se non esiste
if not os.path.exists(vars_file):
    open(vars_file, 'w').close()

# Funzione per aggiungere un account
def add_account(phone_number):
    session_name = f'{sessions_dir}/{phone_number}'
    client = TelegramClient(session_name, api_id, api_hash)

    try:
        # Connetti al client Telegram
        client.connect()

        if not client.is_user_authorized():
            # Se non autorizzato, invia il codice per la verifica
            try:
                client.send_code_request(phone_number)
                code = input(f'Inserisci il codice ricevuto via Telegram per {phone_number}: ')
                client.sign_in(phone_number, code)
            except SessionPasswordNeededError:
                # Se richiesta la password
                password = input(f'Inserisci la tua password per {phone_number}: ')
                client.sign_in(password=password)
        
        # Ottieni informazioni sul tuo account
        me = client.get_me()
        print(f'Successfully logged in as {me.first_name} ({phone_number})')

        # Salva il numero di telefono in vars.txt, evitando duplicati
        with open(vars_file, 'rb') as f:
            existing_numbers = pickle.load(f) if os.path.getsize(vars_file) > 0 else []

        if phone_number not in existing_numbers:
            existing_numbers.append(phone_number)
            with open(vars_file, 'wb') as f:
                pickle.dump(existing_numbers, f)

        print(f'Numero {phone_number} salvato con successo in vars.txt.')

    except Exception as e:
        print(f"Errore durante l'aggiunta dell'account {phone_number}: {e}")
    finally:
        # Disconnessione del client
        client.disconnect()

# Funzione per avviare il bot senza richiedere il numero di telefono
def start_bot():
    # Lista dei numeri di telefono già registrati
    with open(vars_file, 'rb') as f:
        existing_numbers = pickle.load(f) if os.path.getsize(vars_file) > 0 else []

    if not existing_numbers:
        print("Nessun numero di telefono registrato. Devi prima aggiungere un numero.")
        return

    phone_number = existing_numbers[0]  # Prende il primo numero registrato
    session_name = f'{sessions_dir}/{phone_number}'
    client = TelegramClient(session_name, api_id, api_hash)

    try:
        client.connect()
        if not client.is_user_authorized():
            print(f"Il numero {phone_number} non è autorizzato. Autenticazione necessaria.")
            return

        # Ottieni informazioni sull'account
        me = client.get_me()
        print(f'Bot avviato con successo come {me.first_name} ({phone_number})')

        # Inizia a eseguire i comandi del bot o altre operazioni qui

    except Exception as e:
        print(f"Errore nell'avvio del bot: {e}")
    finally:
        # Disconnessione del client
        client.disconnect()

if __name__ == '__main__':
    # Se è il primo avvio, chiede di aggiungere un account
    phone_number = input('Inserisci il numero di telefono con il prefisso internazionale (es. +39...): ')
    add_account(phone_number)
    
    # Dopo aver aggiunto l'account, puoi avviare il bot senza altre interazioni
    start_bot()
