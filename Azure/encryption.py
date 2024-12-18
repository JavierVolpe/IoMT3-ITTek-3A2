from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64
from flask import current_app

def get_aes_key():
    key = current_app.config["SECRET_KEY"]
    if isinstance(key, str):
        key = key.encode('utf-8')
    # Ensure the key is 16, 24, or 32 bytes long for AES
    if len(key) not in (16, 24, 32):
        raise ValueError("SECRET_KEY must be 16, 24, or 32 bytes long for AES encryption.")
    return key

def encrypt_data(plaintext):
    key = get_aes_key()
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))
    return base64.b64encode(cipher.nonce + tag + ciphertext).decode('utf-8')

def decrypt_data(encrypted_text):
    key = get_aes_key()
    try:
        data = base64.b64decode(encrypted_text.encode('utf-8'))
        nonce, tag, ciphertext = data[:16], data[16:32], data[32:]
        cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')
    except (ValueError, KeyError) as e:
        current_app.logger.error(f"Decryption failed: {e}")
        return "Decryption Error"
