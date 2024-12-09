from telethon.sync import TelegramClient
import pickle
import os

# API credentials
api_id = '25373607'
api_hash = '3b559c2461a210c9654399b66125bc0b'

# Directory per le sessioni
sessions_dir = 'sessions'

# File per i numeri di telefono salvati
vars_file = 'vars.txt'

# Assicurati che la cartella per le sessioni esista
if not os.path.exists(sessions_dir):
    os.makedirs(sessions_dir)

if not os.path.exists(vars_file):
    open(vars_file, 'w').close()

# Funzione per caricare il primo numero salvato in vars.txt
def load_first_phone_number():
    with open(vars_file, 'rb') as f:
        if os.path.getsize(vars_file) > 0:
            phone_numbers = pickle.load(f)
            if phone_numbers:
                return phone_numbers[0]  # Ritorna il primo numero salvato
    return None

# Funzione per avviare il bot
def start_bot():
    phone_number = load_first_phone_number()
    
    if not phone_number:
        print("Nessun numero di telefono registrato. Devi prima aggiungere un numero.")
        return

    session_name = f'{sessions_dir}/{phone_number}'
    client = TelegramClient(session_name, api_id, api_hash)

    try:
        client.connect()
        if not client.is_user_authorized():
            print(f"Il numero {phone_number} non è autorizzato. Autenticazione necessaria.")
            return

        me = client.get_me()
        print(f'Bot avviato con successo come {me.first_name} ({phone_number})')

        # Qui puoi aggiungere il codice per eseguire le funzioni del bot
        # Esempio: rimani in ascolto per nuovi comandi
        client.run_until_disconnected()

    except Exception as e:
        print(f"Errore nell'avvio del bot: {e}")
    finally:
        client.disconnect()

if __name__ == '__main__':
    start_bot()
