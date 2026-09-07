"""Fleet inventory — mirrors ~/.ssh/config on MSI."""

FLEET = {
    "steve": {"host": "laptop-bsug4cf9.tailf8336a.ts.net", "user": "ssatt", "os": "windows"},
    "green-machine": {"host": "laptop-po2blkb5.tailf8336a.ts.net", "user": "mikel", "os": "windows"},
    "macbook-air": {"host": "michaels-macbook-air.tailf8336a.ts.net", "user": "michaelcampbell", "os": "macos"},
    "karenold": {"host": "karenold.tailf8336a.ts.net", "user": "karenold", "os": "linux"},
    "turion": {"host": "turion.tailf8336a.ts.net", "user": "mikel", "os": "linux"},
    "aorus": {"host": "localhost", "user": "mikel", "os": "linux"},
}

PRESETS = {
    "windows": {
        "Disk space": "powershell -NoProfile -Command \"Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select DeviceID,@{n='SizeGB';e={[math]::Round($_.Size/1GB,1)}},@{n='FreeGB';e={[math]::Round($_.FreeSpace/1GB,1)}}\"",
        "Uptime": "powershell -NoProfile -Command \"(Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime\"",
        "Check Windows Update": "powershell -NoProfile -Command \"$s=(New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher(); $r=$s.Search('IsInstalled=0 and IsHidden=0'); $r.Updates.Count\"",
        "Top processes (RAM)": "powershell -NoProfile -Command \"Get-Process | Sort WorkingSet64 -Descending | Select -First 10 ProcessName,@{n='RAM_MB';e={[math]::Round($_.WorkingSet64/1MB,0)}}\"",
    },
    "macos": {
        "Disk space": "df -h /",
        "Uptime": "uptime",
        "Top processes (RAM)": "ps aux | sort -rk4 | head -10",
    },
    "linux": {
        "Disk space": "df -h /",
        "Uptime": "uptime",
        "Pool status": "df -h /mnt/4klabs-pool",
        "Pi-hole status": "pihole status",
        "Top processes (RAM)": "ps aux --sort=-%mem | head -10",
    },
}
