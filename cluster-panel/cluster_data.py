"""Parallel data-gathering for the dashboard: online status, disk usage, pool, Pi-hole, LG ThinQ."""
import asyncio
import json as _json
import re
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fleet import FLEET, PRESETS
from ssh_exec import run

DISK_CMD = {
    "windows": "powershell -NoProfile -Command \"Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3 AND DeviceID=\\\"C:\\\"' | Select @{n='FreeGB';e={[math]::Round($_.FreeSpace/1GB,1)}},@{n='SizeGB';e={[math]::Round($_.Size/1GB,1)}} | ConvertTo-Json\"",
    "macos": "df -g / | tail -1 | awk '{print $4, $2}'",
    "linux": "df -BG / | tail -1 | awk '{print $4, $2}'",
}

THINQ_CONFIG = Path("/home/mikel/thinq-scripts/config.json")

STATS_CMD = {
    "windows": (
        "powershell -NoProfile -Command \"$os=Get-CimInstance Win32_OperatingSystem; "
        "$cpu=(Get-CimInstance Win32_Processor | Measure-Object LoadPercentage -Average).Average; "
        "$disk=Get-CimInstance Win32_LogicalDisk -Filter 'DeviceID=\\\"C:\\\"'; "
        "[pscustomobject]@{CpuPct=$cpu;RamUsedGB=[math]::Round(($os.TotalVisibleMemorySize-$os.FreePhysicalMemory)/1MB,1);"
        "RamTotalGB=[math]::Round($os.TotalVisibleMemorySize/1MB,1);"
        "DiskFreeGB=[math]::Round($disk.FreeSpace/1GB,1);DiskTotalGB=[math]::Round($disk.Size/1GB,1)} | ConvertTo-Json\""
    ),
    "macos": (
        "echo CPU:$(top -l 1 -n 0 | grep 'CPU usage' | awk '{print $3}' | tr -d '%'); "
        "df -g / | tail -1 | awk '{print \"DISK:\"$4\"/\"$2}'"
    ),
    "linux": (
        "echo CPU:$(top -bn1 | grep 'Cpu(s)' | awk '{print $2}'); "
        "free -m | awk '/Mem:/ {print \"RAM:\"$3\"/\"$2}'; "
        "df -BG / | tail -1 | awk '{print \"DISK:\"$4\"/\"$2}'"
    ),
}


def _parse_stats(os_name, raw):
    """Best-effort parse into {'cpu':, 'ram':, 'disk':}; falls back to {'raw': raw} if the shape is unexpected."""
    try:
        if os_name == "windows":
            j = _json.loads(raw)
            return {
                "cpu": f"{j['CpuPct']}%" if j.get("CpuPct") is not None else "?",
                "ram": f"{j['RamUsedGB']} / {j['RamTotalGB']} GB",
                "disk": f"{j['DiskFreeGB']} GB free / {j['DiskTotalGB']} GB",
            }
        fields = {}
        for line in raw.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                fields[key.strip().upper()] = val.strip()
        out = {"cpu": f"{fields['CPU']}%" if "CPU" in fields else "?"}
        if "RAM" in fields:
            out["ram"] = fields["RAM"] + " MB"
        if "DISK" in fields:
            free, _, total = fields["DISK"].partition("/")
            out["disk"] = f"{free}GB free / {total}GB"
        return out
    except Exception:
        return {"raw": raw}


def _stats_for(name, machine):
    cmd = STATS_CMD[machine["os"]]
    result = run(machine["host"], machine["user"], cmd, timeout=15)
    if not result["ok"]:
        return name, None
    return name, _parse_stats(machine["os"], result["stdout"].strip())


def get_resource_stats_all():
    """Runs CPU/RAM/disk checks on every machine concurrently. Returns {name: parsed_dict_or_None}."""
    with ThreadPoolExecutor(max_workers=len(FLEET)) as ex:
        results = list(ex.map(lambda kv: _stats_for(kv[0], kv[1]), FLEET.items()))
    return dict(results)


def get_tailscale_status():
    """Returns {device_name: {'ip':..., 'online': bool, 'os':...}} by parsing `tailscale status`."""
    try:
        out = subprocess.run(["tailscale", "status"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return {}
    devices = {}
    for line in out.strip().splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        ip, name, _user, os_ = parts[0], parts[1], parts[2], parts[3]
        online = "offline" not in line
        devices[name] = {"ip": ip, "online": online, "os": os_}
    return devices


def _disk_for(name, machine):
    cmd = DISK_CMD[machine["os"]]
    result = run(machine["host"], machine["user"], cmd, timeout=15)
    if not result["ok"]:
        return name, None
    return name, result["stdout"].strip()


def get_disk_usage_all():
    """Runs disk-space checks on every machine concurrently. Returns {name: raw_output_or_None}."""
    with ThreadPoolExecutor(max_workers=len(FLEET)) as ex:
        results = list(ex.map(lambda kv: _disk_for(kv[0], kv[1]), FLEET.items()))
    return dict(results)


def get_pool_status():
    result = run("localhost", "mikel", "df -h /mnt/4klabs-pool | tail -1", timeout=10)
    if not result["ok"]:
        return None
    parts = result["stdout"].split()
    if len(parts) < 5:
        return None
    return {"size": parts[1], "used": parts[2], "avail": parts[3], "pct": parts[4]}


def get_pihole_stats():
    result = run("localhost", "mikel", "pihole -c -j 2>/dev/null || echo '{}'", timeout=10)
    return result["stdout"].strip() if result["ok"] else None


async def _thinq_status():
    import aiohttp
    from thinqconnect import ThinQApi

    cfg = _json.loads(THINQ_CONFIG.read_text())
    async with aiohttp.ClientSession() as session:
        api = ThinQApi(
            session=session,
            access_token=cfg["access_token"],
            country_code=cfg["country"],
            client_id=f"cluster-panel-{uuid.uuid4()}",
        )
        devices = await api.async_get_device_list()
        results = []
        for d in devices:
            info = d["deviceInfo"]
            status = await api.async_get_device_status(d["deviceId"])
            state = status.get("runState", {}).get("currentState", "?")
            results.append({"alias": info.get("alias") or info["deviceType"], "state": state})
        return results


def get_thinq_status():
    """Returns [{'alias':..., 'state':...}] for each LG ThinQ appliance, or None on failure."""
    if not THINQ_CONFIG.exists():
        return None
    try:
        return asyncio.run(_thinq_status())
    except Exception:
        return None
