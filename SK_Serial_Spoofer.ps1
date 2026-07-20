# ============================================================
#  MTA:SA SERIAL SPOOFER — جميع الحقوق لـ SILENCE KILLER 5x08
#  لدي إذن ومخوّل لإجراء اختبار الاختراق هذا
#  البصمة الرقمية: SK5x08-MTA-SPOOF-v1
# ============================================================

param([string]$SK5x08_TargetSerial = "891EDB0984D1211FFEE5811D677E1234")

$host.UI.RawUI.WindowTitle = "SK5x08 | MTA Serial Spoofer"
$ErrorActionPreference = "SilentlyContinue"

$SK5x08_Admin = ([System.Security.Principal.WindowsIdentity]::GetCurrent().Groups -match "S-1-5-32-544")
if (-not $SK5x08_Admin) {
    Write-Host "[!] Administrator Required" -ForegroundColor Red
    pause
    exit
}

function SK5x08_Menu {
    Clear-Host
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "   MTA:SA SERIAL SPOOFER - SILENCE KILLER 5x08" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Target: $SK5x08_TargetSerial" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  [1] Spoof Serial" -ForegroundColor Green
    Write-Host "  [2] Spoof MAC" -ForegroundColor Green
    Write-Host "  [3] Full Bypass" -ForegroundColor Green
    Write-Host "  [4] Restore" -ForegroundColor Red
    Write-Host "  [5] Status" -ForegroundColor Yellow
    Write-Host "  [6] Exit" -ForegroundColor Gray
    Write-Host ""
}

function SK5x08_Serial {
    Write-Host "[*] Registry spoof..." -ForegroundColor Yellow
    $SK5x08_Path = "HKLM:\SOFTWARE\WOW6432Node\Multi Theft Auto: San Andreas All\1.6\Settings\general"
    $SK5x08_Rand = -join ((65..90) + (97..122) | Get-Random -Count 16 | ForEach-Object { [char]$_ })
    $SK5x08_Num = Get-Random -Minimum 10000 -Maximum 999999
    $SK5x08_Checksum = "$SK5x08_TargetSerial`:$SK5x08_Rand`:$SK5x08_Num"
    New-ItemProperty -Path $SK5x08_Path -Name "cachechecksum" -Value $SK5x08_Checksum -PropertyType String -Force | Out-Null
    $SK5x08_Alts = @(
        "HKLM:\SOFTWARE\Multi Theft Auto: San Andreas All\1.6\Settings\general",
        "HKCU:\SOFTWARE\Multi Theft Auto: San Andreas All\1.6\Settings\general",
        "HKCU:\SOFTWARE\WOW6432Node\Multi Theft Auto: San Andreas All\1.6\Settings\general"
    )
    foreach ($SK5x08_A in $SK5x08_Alts) {
        New-ItemProperty -Path $SK5x08_A -Name "cachechecksum" -Value $SK5x08_Checksum -PropertyType String -Force -ErrorAction SilentlyContinue | Out-Null
    }
    $SK5x08_Cache = "$env:LOCALAPPDATA\MTA San Andreas\cache"
    if (Test-Path $SK5x08_Cache) {
        Remove-Item "$SK5x08_Cache\*" -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Host "[+] Serial -> $SK5x08_TargetSerial" -ForegroundColor Green
}

function SK5x08_MAC {
    Write-Host "[*] MAC spoof..." -ForegroundColor Yellow
    $SK5x08_B = @(0x00)
    for ($i = 0; $i -lt 5; $i++) {
        $SK5x08_B += Get-Random -Minimum 0 -Maximum 255
    }
    $SK5x08_NMAC = ($SK5x08_B | ForEach-Object { $_.ToString("X2") }) -join ":"
    $SK5x08_Base = "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"
    $SK5x08_Adps = Get-NetAdapter | Where-Object { $_.Status -eq "Up" }
    foreach ($SK5x08_A in $SK5x08_Adps) {
        Get-ChildItem $SK5x08_Base -ErrorAction SilentlyContinue | Where-Object { $_.PSChildName -match "^\d{4}$" } | ForEach-Object {
            $SK5x08_D = (Get-ItemProperty -Path $_.PSPath -Name "DriverDesc" -ErrorAction SilentlyContinue).DriverDesc
            if ($SK5x08_D -and $SK5x08_D -eq $SK5x08_A.Name) {
                Set-ItemProperty -Path $_.PSPath -Name "NetworkAddress" -Value $SK5x08_NMAC.Replace(":", "") -Type String
            }
        }
        try {
            Disable-NetAdapter -Name $SK5x08_A.Name -Confirm:$false -ErrorAction Stop
            Start-Sleep -Seconds 2
            Enable-NetAdapter -Name $SK5x08_A.Name -Confirm:$false -ErrorAction Stop
        } catch {
            Write-Host "[-] MAC toggle failed for $($SK5x08_A.Name)" -ForegroundColor Red
        }
    }
    Write-Host "[+] MAC -> $SK5x08_NMAC" -ForegroundColor Green
}

function SK5x08_Full {
    Write-Host "============================================================" -ForegroundColor Magenta
    Write-Host "   FULL BYPASS - SILENCE KILLER 5x08" -ForegroundColor Magenta
    Write-Host "============================================================" -ForegroundColor Magenta
    SK5x08_Serial
    Start-Sleep -Seconds 1
    SK5x08_MAC
    Start-Sleep -Seconds 1
    ipconfig /flushdns | Out-Null
    arp -d * | Out-Null
    nbtstat -R | Out-Null
    Remove-Item "$env:LOCALAPPDATA\MTA San Andreas\crashdumps\*" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item "$env:LOCALAPPDATA\MTA San Andreas\CrashLogs\*" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "[+] FULL BYPASS DONE - SILENCE KILLER 5x08" -ForegroundColor Green
    Write-Host "[!] Reboot required" -ForegroundColor Yellow
}

function SK5x08_Restore {
    $SK5x08_RPaths = @(
        "HKLM:\SOFTWARE\WOW6432Node\Multi Theft Auto: San Andreas All",
        "HKLM:\SOFTWARE\Multi Theft Auto: San Andreas All",
        "HKCU:\SOFTWARE\Multi Theft Auto: San Andreas All",
        "HKCU:\SOFTWARE\WOW6432Node\Multi Theft Auto: San Andreas All"
    )
    foreach ($SK5x08_R in $SK5x08_RPaths) {
        if (Test-Path $SK5x08_R) {
            Remove-Item $SK5x08_R -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    $SK5x08_RB = "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"
    Get-ChildItem $SK5x08_RB -ErrorAction SilentlyContinue | Where-Object { $_.PSChildName -match "^\d{4}$" } | ForEach-Object {
        Remove-ItemProperty $_.PSPath -Name "NetworkAddress" -ErrorAction SilentlyContinue | Out-Null
    }
    Write-Host "[+] Restored" -ForegroundColor Green
}

function SK5x08_Status {
    $SK5x08_S = (Get-ItemProperty -Path "HKLM:\SOFTWARE\WOW6432Node\Multi Theft Auto: San Andreas All\1.6\Settings\general" -Name "cachechecksum" -ErrorAction SilentlyContinue).cachechecksum
    if ($SK5x08_S) {
        Write-Host "Serial: $SK5x08_S" -ForegroundColor White
    } else {
        Write-Host "No serial found" -ForegroundColor Gray
    }
    Write-Host "Target: $SK5x08_TargetSerial" -ForegroundColor Cyan
}

# Main loop
do {
    SK5x08_Menu
    $SK5x08_C = Read-Host ">"
    switch ($SK5x08_C) {
        "1" { SK5x08_Serial }
        "2" { SK5x08_MAC }
        "3" { SK5x08_Full }
        "4" { SK5x08_Restore }
        "5" { SK5x08_Status }
        "6" { break }
    }
    if ($SK5x08_C -ne "6") {
        Write-Host "`nPress any key..."
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
} while ($SK5x08_C -ne "6")
