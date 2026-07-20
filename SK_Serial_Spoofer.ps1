# ============================================================
#  MTA:SA SERIAL SPOOFER - جميع الحقوق لـ SILENCE KILLER 5x08
#  البصمة : SK5x08-MTA-SPOOF-v2
# ============================================================

$host.UI.RawUI.WindowTitle = "SK5x08 | MTA Serial Spoofer"
$ErrorActionPreference = "SilentlyContinue"

$SK5x08_Admin = ([System.Security.Principal.WindowsIdentity]::GetCurrent().Groups -match "S-1-5-32-544")
if (-not $SK5x08_Admin) { Write-Host "[!] Administrator Required" -ForegroundColor Red; pause; exit }

function SK5x08_Spoof {
    param([string]$SK5x08_Serial)
    $SK5x08_Path = "HKLM:\SOFTWARE\WOW6432Node\Multi Theft Auto: San Andreas All\1.5\Settings\general"
    $SK5x08_Rand = -join ((65..90) + (97..122) | Get-Random -Count 16 | ForEach-Object { [char]$_ })
    $SK5x08_Num = Get-Random -Minimum 10000 -Maximum 999999
    $SK5x08_Checksum = "$SK5x08_Serial`:$SK5x08_Rand`:$SK5x08_Num"
    New-ItemProperty -Path $SK5x08_Path -Name "cachechecksum" -Value $SK5x08_Checksum -PropertyType String -Force | Out-Null
    $SK5x08_Alts = @("HKLM:\SOFTWARE\Multi Theft Auto: San Andreas All\1.5\Settings\general","HKCU:\SOFTWARE\Multi Theft Auto: San Andreas All\1.5\Settings\general","HKCU:\SOFTWARE\WOW6432Node\Multi Theft Auto: San Andreas All\1.5\Settings\general")
    foreach ($SK5x08_A in $SK5x08_Alts) { New-ItemProperty -Path $SK5x08_A -Name "cachechecksum" -Value $SK5x08_Checksum -PropertyType String -Force -ErrorAction SilentlyContinue | Out-Null }
    $SK5x08_Cache = "$env:LOCALAPPDATA\MTA San Andreas\cache"
    if (Test-Path $SK5x08_Cache) { Remove-Item "$SK5x08_Cache\*" -Recurse -Force -ErrorAction SilentlyContinue }
    Write-Host "[+] Serial -> $SK5x08_Serial" -ForegroundColor Green
}

function SK5x08_RandomSerial {
    $SK5x08_Chars = (48..57) + (65..90) + (97..122)
    $SK5x08_Serial = -join ($SK5x08_Chars | Get-Random -Count 32 | ForEach-Object { [char]$_ })
    return $SK5x08_Serial
}

do {
    Clear-Host
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "   MTA:SA SERIAL SPOOFER - by silence killer 5x08" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  [1] Custom Serial" -ForegroundColor Green
    Write-Host "  [2] Random Serial" -ForegroundColor Yellow
    Write-Host "  [3] Exit" -ForegroundColor Red
    Write-Host ""
    $SK5x08_C = Read-Host ">"
    
    switch ($SK5x08_C) {
        "1" {
            Write-Host ""
            $SK5x08_Input = Read-Host "Enter serial 32 characters"
            if ($SK5x08_Input.Length -eq 32) {
                SK5x08_Spoof -SK5x08_Serial $SK5x08_Input
            } else {
                Write-Host "[-] Must be 32 characters" -ForegroundColor Red
            }
        }
        "2" {
            $SK5x08_New = SK5x08_RandomSerial
            SK5x08_Spoof -SK5x08_Serial $SK5x08_New
        }
        "3" { break }
    }
    
    if ($SK5x08_C -ne "3") {
        Write-Host "`nPress any key..."
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
} while ($SK5x08_C -ne "3")
