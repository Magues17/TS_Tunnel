# Run this in an ELEVATED PowerShell (Run as Administrator) on any Windows machine
# joining the cluster. Idempotent - safe to re-run.

$ErrorActionPreference = 'Continue'
$pubKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFZiBsO0zAT8DnW0VpASr2ss2grPj8zjkkjCjGmMU8/n msi-cluster-control"

Write-Host "=== Installing OpenSSH Server ==="
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 | Out-Null
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic

Write-Host "=== Firewall rule ==="
if (-not (Get-NetFirewallRule -Name OpenSSH-Server-In-TCP -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name OpenSSH-Server-In-TCP -DisplayName 'OpenSSH Server (sshd)' `
        -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
}

Write-Host "=== Installing cluster key (admin + user paths, covers either case) ==="
$adminKeyFile = "$env:ProgramData\ssh\administrators_authorized_keys"
if (-not (Test-Path $adminKeyFile) -or -not (Select-String -Path $adminKeyFile -Pattern ([regex]::Escape($pubKey)) -Quiet -ErrorAction SilentlyContinue)) {
    Add-Content -Path $adminKeyFile -Value $pubKey
}
C:\Windows\System32\icacls.exe $adminKeyFile /inheritance:r | Out-Null
C:\Windows\System32\icacls.exe $adminKeyFile /grant "SYSTEM:F" "Administrators:F" | Out-Null

$userSshDir = "$env:USERPROFILE\.ssh"
$userKeyFile = "$userSshDir\authorized_keys"
if (-not (Test-Path $userSshDir)) { New-Item -ItemType Directory -Path $userSshDir | Out-Null }
if (-not (Test-Path $userKeyFile) -or -not (Select-String -Path $userKeyFile -Pattern ([regex]::Escape($pubKey)) -Quiet -ErrorAction SilentlyContinue)) {
    Add-Content -Path $userKeyFile -Value $pubKey
}

Write-Host "=== Creating 4KLABS folder ==="
if (-not (Test-Path "C:\4KLABS")) { New-Item -ItemType Directory -Path "C:\4KLABS" | Out-Null }

Write-Host ""
Write-Host "=== DONE. Send these back for SSH config: ==="
Write-Host ("Hostname: " + $env:COMPUTERNAME)
Write-Host ("Username: " + $env:USERNAME)
