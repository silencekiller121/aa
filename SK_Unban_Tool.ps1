# ============================================================
#  MTA:SA UNBAN TOOL - جميع الحقوق لـ SILENCE KILLER 5x08
#  البصمة الرقمية: SK5x08-MTA-UNBAN-v1
# ============================================================

$host.UI.RawUI.WindowTitle = "SK5x08 | MTA Unban"
$ErrorActionPreference = "SilentlyContinue"

$SK5x08_Admin = ([System.Security.Principal.WindowsIdentity]::GetCurrent().Groups -match "S-1-5-32-544")
if (-not $SK5x08_Admin) { Write-Host "[!] Administrator Required" -ForegroundColor Red; pause; exit }

function SK5x08_Menu {
    Clear-Host
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "   MTA:SA UNBAN TOOL - SILENCE KILLER 5x08" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  [1] Quick Unban" -ForegroundColor Green
    Write-Host "  [2] Full Unban" -ForegroundColor Green
    Write-Host "  [3] Change Volume ID" -ForegroundColor Yellow
    Write-Host "  [4] Check IDs" -ForegroundColor Cyan
    Write-Host "  [5] Exit" -ForegroundColor Gray
    Write-Host ""
}

function SK5x08_Clean {
    Get-Process "gta_sa","MTA","Multi Theft Auto*","netc" -ErrorAction SilentlyContinue | Stop-Process -Force
    $SK5x08_RP = @("HKLM:\SOFTWARE\WOW6432Node\Multi Theft Auto: San Andreas All","HKLM:\SOFTWARE\Multi Theft Auto: San Andreas All","HKCU:\SOFTWARE\Multi Theft Auto: San Andreas All","HKCU:\SOFTWARE\WOW6432Node\Multi Theft Auto: San Andreas All")
    foreach ($SK5x08_P in $SK5x08_RP) { if (Test-Path $SK5x08_P) { Remove-Item $SK5x08_P -Recurse -Force } }
    $SK5x08_FD = @("$env:LOCALAPPDATA\MTA San Andreas","$env:APPDATA\MTA San Andreas","$env:ProgramFiles\MTA San Andreas","${env:ProgramFiles(x86)}\MTA San Andreas")
    foreach ($SK5x08_F in $SK5x08_FD) { if (Test-Path $SK5x08_F) { try { Remove-Item $SK5x08_F -Recurse -Force } catch {} } }
    Remove-Item "$env:TEMP\*mta*","$env:TEMP\*gta*","$env:TEMP\*.mtabin" -Force -ErrorAction SilentlyContinue
}

function SK5x08_MachineGUID {
    $SK5x08_NG = [guid]::NewGuid().ToString()
    Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Cryptography" -Name "MachineGuid" -Value $SK5x08_NG
    Write-Host "[+] MachineGuid -> $SK5x08_NG" -ForegroundColor Green
}

function SK5x08_HwProfileGUID {
    $SK5x08_NG = [guid]::NewGuid().ToString()
    Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\IDConfigDB\Hardware Profiles\0001" -Name "HwProfileGuid" -Value "{$SK5x08_NG}"
    Write-Host "[+] HwProfileGuid -> {$SK5x08_NG}" -ForegroundColor Green
}

function SK5x08_ComputerName {
    $SK5x08_NN = "SK5x08-" + -join ((65..90) | Get-Random -Count 7 | ForEach-Object { [char]$_ })
    Rename-Computer -NewName $SK5x08_NN -Force -ErrorAction SilentlyContinue
    Write-Host "[+] ComputerName -> $SK5x08_NN (after reboot)" -ForegroundColor Green
}

function SK5x08_VolumeID {
    $SK5x08_VI = $null
    $SK5x08_VPaths = @("C:\VolumeID\volumeid64.exe","C:\VolumeID\volumeid.exe",".\volumeid64.exe",".\volumeid.exe")
    foreach ($SK5x08_V in $SK5x08_VPaths) { if (Test-Path $SK5x08_V) { $SK5x08_VI = $SK5x08_V; break } }
    if (-not $SK5x08_VI) { Write-Host "[-] VolumeID.exe missing (download sysinternals)" -ForegroundColor Red; return }
    $SK5x08_NS = -join ((0..9)+('A'..'F') | Get-Random -Count 4) + "-" + -join ((0..9)+('A'..'F') | Get-Random -Count 4)
    $SK5x08_VD = Split-Path $SK5x08_VI -Parent
    $SK5x08_VN = Split-Path $SK5x08_VI -Leaf
    Start-Process $SK5x08_VN "C: $SK5x08_NS" -WorkingDirectory $SK5x08_VD -NoNewWindow -Wait
    Write-Host "[+] VolumeID -> $SK5x08_NS (after reboot)" -ForegroundColor Green
}

function SK5x08_MAC {
    $SK5x08_B = @(0x00); for ($i=0;$i -lt 5;$i++) { $SK5x08_B += Get-Random -Minimum 0 -Maximum 255 }
    $SK5x08_NM = ($SK5x08_B | ForEach-Object { $_.ToString("X2") }) -join ":"
    $SK5x08_BR = "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"
    $SK5x08_AD = Get-NetAdapter | Where-Object { $_.Status -eq "Up" }
    foreach ($SK5x08_A in $SK5x08_AD) {
        Get-ChildItem $SK5x08_BR -ErrorAction SilentlyContinue | Where-Object { $_.PSChildName -match "^\d{4}$" } | ForEach-Object {
            $SK5x08_D = (Get-ItemProperty $_.PSPath -Name "DriverDesc" -ErrorAction SilentlyContinue).DriverDesc
            if ($SK5x08_D -and $SK5x08_D -eq $SK5x08_A.Name) { Set-ItemProperty $_.PSPath -Name "NetworkAddress" -Value $SK5x08_NM.Replace(":","") -Type String }
        }
        try { Disable-NetAdapter $SK5x08_A.Name -Confirm:$false -ErrorAction Stop; Start-Sleep -Seconds 2; Enable-NetAdapter $SK5x08_A.Name -Confirm:$false -ErrorAction Stop } catch {}
    }
    Write-Host "[+] MAC -> $SK5x08_NM" -ForegroundColor Green
}

function SK5x08_Quick {
    Clear-Host
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "   QUICK UNBAN - SILENCE KILLER 5x08" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    SK5x08_Clean; Start-Sleep -Seconds 1
    SK5x08_MachineGUID; Start-Sleep -Seconds 1
    SK5x08_HwProfileGUID; Start-Sleep -Seconds 1
    SK5x08_ComputerName
    Write-Host "`n[+] QUICK UNBAN DONE - SILENCE KILLER 5x08" -ForegroundColor Green
    Write-Host "[!] Reboot then reinstall MTA" -ForegroundColor Red
}

function SK5x08_Full {
    Clear-Host
    Write-Host "============================================================" -ForegroundColor Magenta
    Write-Host "   FULL UNBAN - SILENCE KILLER 5x08" -ForegroundColor Magenta
    Write-Host "============================================================" -ForegroundColor Magenta
    SK5x08_Clean; Start-Sleep -Seconds 1
    SK5x08_MachineGUID; Start-Sleep -Seconds 1
    SK5x08_HwProfileGUID; Start-Sleep -Seconds 1
    SK5x08_ComputerName; Start-Sleep -Seconds 1
    SK5x08_VolumeID; Start-Sleep -Seconds 1
    SK5x08_MAC
    Write-Host "`n[+] FULL UNBAN DONE - SILENCE KILLER 5x08" -ForegroundColor Green
    Write-Host "[!] Reboot then reinstall MTA" -ForegroundColor Red
}

function SK5x08_ShowIDs {
    $SK5x08_MG = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Cryptography" -Name "MachineGuid" -ErrorAction SilentlyContinue).MachineGuid
    $SK5x08_HW = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\IDConfigDB\Hardware Profiles\0001" -Name "HwProfileGuid" -ErrorAction SilentlyContinue).HwProfileGuid
    $SK5x08_VL = (Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'").VolumeSerialNumber
    Write-Host "MachineGuid:   $SK5x08_MG" -ForegroundColor White
    Write-Host "HwProfileGuid: $SK5x08_HW" -ForegroundColor White
    Write-Host "ComputerName:  $env:COMPUTERNAME" -ForegroundColor White
    Write-Host "VolumeSerial:  $SK5x08_VL" -ForegroundColor White
}

do {
    SK5x08_Menu
    $SK5x08_C = Read-Host ">"
    switch ($SK5x08_C) {
        "1" { SK5x08_Quick }
        "2" { SK5x08_Full }
        "3" { SK5x08_VolumeID }
        "4" { SK5x08_ShowIDs }
        "5" { break }
    }
    if ($SK5x08_C -ne "5") { Write-Host "`nPress any key..."; $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") }
} while ($SK5x08_C -ne "5")