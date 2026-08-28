# ============================================
# Script: 12_cyberchef_decrypt.ps1
# Uso: powershell -ExecutionPolicy Bypass -File 12_cyberchef_decrypt.ps1
# ============================================

# URL de CyberChef con la receta para descifrar
Write-Host "=== CyberChef Recipe para SmarterMail ===" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Ve a: https://cyberchef.io"
Write-Host "2. Pega la contraseña cifrada"
Write-Host "3. Agrega las siguientes operaciones en orden:"
Write-Host ""
Write-Host "   [From Base64]"
Write-Host "     - Alphabet: A-Za-z0-9+/="
Write-Host "     - Remove non-alphabet chars: true"
Write-Host ""
Write-Host "   [DES Decrypt]"
Write-Host "     - Key (Hex): b43f84d110b4e991"
Write-Host "     - IV (Hex): 01d8aee649ad9227"
Write-Host "     - Mode: CBC"
Write-Host "     - Input: Raw"
Write-Host "     - Output: Raw"
Write-Host ""
Write-Host "4. Ejecuta y obtén la contraseña en texto plano"
Write-Host ""
Write-Host "Ejemplo de URL completa:"
Write-Host "https://cyberchef.io/#recipe=From_Base64('A-Za-z0-9%2B/%3D',true)DES_Decrypt(%7B'option':'Hex','string':'b43f84d110b4e991'%7D,%7B'option':'Hex','string':'01d8aee649ad9227'%7D,'CBC','Raw','Raw')&input=ZjkzMTIwZWI5NTAxOGNhNjM4NzliYjliODgyNDYwMjg"

# Contraseñas comunes encontradas
Write-Host ""
Write-Host "=== Contraseñas Encontradas ===" -ForegroundColor Green
$passwords = @{
    "66e7ppLOBF7UdzDv7zK6MJ1rmyUb1Cby" = "RiverDragon#Storm25"
    "f93120eb95018ca63879bb9b88246028" = "SunsetMountainPeak@2025"
}

foreach ($enc in $passwords.Keys) {
    Write-Host "[+] $enc -> $($passwords[$enc])"
}
