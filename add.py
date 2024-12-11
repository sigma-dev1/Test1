from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
import pickle
import os
import re

# Configurazione delle credenziali
api_id = '25373607'
api_hash = '3b559c2461a210c9654399b66125bc0b'

def validate_phone_number(phone_number):
    """Convalida il formato del numero di telefono"""
    pattern = r'^\+[1-9]\d{1,14}$'
    return re.match(pattern, phone_number) is not None

def add_account(phone_number):
    # Verifica del formato del numero di telefono
    if not validate_phone_number(phone_number):
        print("Formato numero di telefono non valido. Usare il prefisso internazionale (es. +39...).")
        return None

    # Assicurati che le cartelle necessarie esistano
    os.makedirs('sessions', exist_ok=True)

    # Nome sessione basato sul numero di telefono
    session_file = f'sessions/{phone_number}.session'
    
    client = TelegramClient(session_file, api_id, api_hash)
    
    try:
        client.connect()
        
        if not client.is_user_authorized():
            try:
                # Richiesta del codice di verifica
                client.send_code_request(phone_number)
                code = input(f'Inserisci il codice ricevuto via Telegram per {phone_number}: ')
                
                # Tentativo di login
                client.sign_in(phone_number, code)
            
            except SessionPasswordNeededError:
                # Gestione dell'autenticazione a due fattori
                password = input(f'Inserisci la tua password a due fattori per {phone_number}: ')
                client.sign_in(password=password)
        
        # Ottieni informazioni utente
        me = client.get_me()
        print(f'Login riuscito come {me.first_name} ({phone_number})')
        
        # Salvataggio sicuro dei numeri
        save_phone_number(phone_number)
        
        return client
    
    except Exception as e:
        print(f"Errore durante l'aggiunta dell'account: {e}")
        return None
    finally:
        if 'client' in locals():
            client.disconnect()

def save_phone_number(phone_number):
    """Salva i numeri di telefono in modo sicuro"""
    try:
        # Se il file non esiste, lo crea
        if not os.path.exists('vars.txt'):
            open('vars.txt', 'w').close()
        
        # Leggi i numeri esistenti
        existing_numbers = load_phone_numbers()
        
        # Aggiungi il nuovo numero solo se non è già presente
        if phone_number not in existing_numbers:
            with open('vars.txt', 'ab') as f:
                pickle.dump([phone_number], f)
            print(f"Numero {phone_number} salvato con successo.")
        else:
            print(f"Numero {phone_number} già presente.")
    
    except Exception as e:
        print(f"Errore nel salvataggio del numero: {e}")

def load_phone_numbers():
    """Carica i numeri di telefono salvati"""
    numbers = []
    try:
        with open('vars.txt', 'rb') as f:
            while True:
                try:
                    number = pickle.load(f)
                    numbers.extend(number)
                except EOFError:
                    break
    except FileNotFoundError:
        pass
    return numbers

if __name__ == '__main__':
    phone_number = input('Inserisci il numero di telefono con il prefisso internazionale (es. +39...): ')
    add_account(phone_number)
