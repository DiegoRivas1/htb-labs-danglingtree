#!/usr/bin/env python3
# ============================================
# Script: 11_smartmail_decrypt.py
# Uso: python3 11_smartmail_decrypt.py <password_encrypted>
# Ejemplo: python3 11_smartmail_decrypt.py "66e7ppLOBF7UdzDv7zK6MJ1rmyUb1Cby"
# ============================================

import base64
import sys
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

def decrypt_smartmail_password(encrypted_password):
    """
    Descifra contraseñas de SmarterMail usando AES-CBC
    Key: b43f84d110b4e991
    IV: 01d8aee649ad9227
    """
    try:
        # Clave e IV de SmarterMail.Standard.dll
        key = bytes.fromhex("b43f84d110b4e991")
        iv = bytes.fromhex("01d8aee649ad9227")
        
        # Decodificar Base64
        ciphertext = base64.b64decode(encrypted_password)
        
        # Descifrar
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Remover padding (PKCS7)
        pad_len = plaintext[-1]
        if pad_len < 16:
            plaintext = plaintext[:-pad_len]
        
        return plaintext.decode('utf-8', errors='ignore')
    except Exception as e:
        return f"Error descifrando: {str(e)}"

def main():
    if len(sys.argv) < 2:
        print("=" * 50)
        print("SmarterMail Password Decryptor")
        print("=" * 50)
        print("Uso:")
        print(f"  {sys.argv[0]} <password_encrypted>")
        print("\nEjemplo:")
        print(f"  {sys.argv[0]} 66e7ppLOBF7UdzDv7zK6MJ1rmyUb1Cby")
        print("\nTambién puedes usar CyberChef:")
        print("  https://cyberchef.io/#recipe=From_Base64('A-Za-z0-9%2B/%3D',true)DES_Decrypt(%7B'option':'Hex','string':'b43f84d110b4e991'%7D,%7B'option':'Hex','string':'01d8aee649ad9227'%7D,'CBC','Raw','Raw')")
        sys.exit(1)
    
    encrypted = sys.argv[1]
    result = decrypt_smartmail_password(encrypted)
    print(f"\n[+] Contraseña descifrada: {result}")

if __name__ == "__main__":
    main()
