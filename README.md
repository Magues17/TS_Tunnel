# 4KLABS Cluster

A home compute cluster built from a heterogeneous fleet of personal machines, connected via Tailscale. Started as an SSH-onboarding project, grew into a full home server stack: pooled storage, ad-blocking DNS, home automation, a Kubernetes cluster, and a web control panel.

## Current Fleet

| Name | Role | OS | Location | Access |
|---|---|---|---|---|
| **MSI** | Host machine — runs Claude Code, admin workstation | Windows | Home | n/a (local) |
| **Aorus** (`mikel-z390-aorus-master`) | Main server: storage pool, Pi-hole, Home Assistant, Control Panel | Ubuntu Desktop | Home (wired) | `ssh aorus` |
| **Turion** | k3s control-plane node | Ubuntu Server | Mother-in-law's house (Wi-Fi) | `ssh turion` |
| **karenold** | k3s worker node (formerly the Windows "Karen" laptop, wiped and repurposed) | Ubuntu Server | Mother-in-law's house (Wi-Fi) | `ssh karenold` |
| **Green Machine** | Windows workstation, contributes `D:\4KLABS` share to the storage pool | Windows | Home | `ssh green-machine` |
| **Steve** | Being converted to a k3s node (fresh Ubuntu Server install in progress) | Ubuntu Server | Home | pending onboarding |
| **MacBook Air** | Client only — mounts the storage pool at `~/K` | macOS | Home | `ssh macbook-air` |

SSH aliases are defined in `~/.ssh/config` on MSI, all using the dedicated `~/.ssh/cluster_key` (interactive/admin use — distinct from `panel_key`, which the Control Panel's backend uses for its own automated SSH calls).

**Retired:** the original "Karen" (Windows) and "DaddyPC" (Windows) no longer exist as such — that hardware is now `karenold` and `Aorus` respectively.

## Services (all hosted on Aorus)

### Storage pool (`/mnt/4klabs-pool`, mapped as `K:` on Windows / `~/K` on macOS)
- **mergerfs** union of three sources, no file sharding — each file lives on exactly one physical disk, so a drive failure only loses that drive's files:
  - `/mnt/sources/local-d`, `/mnt/sources/local-e` — Aorus's own local NTFS disks (`/etc/fstab`, `nofail,force` — the `force` flag is needed because these drives came from a Windows-to-Linux transition and can flag "dirty" after any unclean shutdown)
  - `/mnt/sources/green-machine` — CIFS mount of Green Machine's `D:\4KLABS` share (`nofail,x-systemd.automount` — critical, see Gotchas below)
- Exported via **Samba** (`[4KLABS]` share, user `mikel`) — password stored in `/etc/samba/creds/green-machine` and known to the user, not committed here
- Windows machines: `net use K: \\mikel-z390-aorus-master.tailf8336a.ts.net\4KLABS ... /persistent:yes`
- macOS: LaunchAgent at `~/Library/LaunchAgents/com.4klabs.mountk.plist` auto-mounts at login

### Pi-hole (network-wide ad blocking)
- Runs on Aorus, static LAN IP `192.168.1.230`
- Tailscale admin console → DNS → Global Nameservers points the whole tailnet at Aorus's Tailscale IP
- Router DHCP also pushes Aorus as DNS to the whole physical LAN (covers non-Tailscale devices: smart TV, litter box, washer/dryer)
- **Critical config**: `/etc/pihole/pihole.toml` → `dns.revServers` must include a conditional-forward rule for `tailf8336a.ts.net` to Tailscale's resolver (`100.100.100.100`), or MagicDNS hostnames break tailnet-wide the moment Pi-hole becomes the DNS authority. See Gotchas.

### Home Assistant
- `~/homeassistant` (Python venv install), systemd service `home-assistant.service`
- HTTPS via the same mkcert cert as everything else on Aorus
- `use_x_frame_options: false` required so it can be embedded in the Control Panel's iframe
- Onboarding wizard (admin account, location) must be completed once via the web UI — see Gotchas for a config-migration trap if you ever add `http:` SSL settings after the first boot

### Cluster Control Panel (`~/cluster-panel`)
- Streamlit app, systemd service `cluster-panel.service`, HTTPS on port `27887`, bound to Aorus's **Tailscale IP** (not LAN IP — tailnet-only by design)
- Google OAuth login (`auth.py`), allowlist in `.streamlit/secrets.toml` (`allowed_emails`)
- Pages: `Dashboard` (fleet status, storage, Pi-hole stats, LG ThinQ appliance status), `Home` (Home Assistant iframe), `Control` (owner-only: SSH quick-commands + a `clusterssh://` protocol-handler button that opens a real PowerShell window on the viewer's own machine — see `cluster-tools/launch-ssh.ps1` on MSI and the matching registry entry under `HKCU\Software\Classes\clusterssh`)
- `fleet.py` is the single source of truth for what shows up in the panel — keep it in sync with `~/.ssh/config`
- Front door: `136stable.rd` — a tiny unauthenticated redirect service (`front-door.service`, port `27886`) that bounces to the real HTTPS panel, resolved via a Pi-hole local DNS record. Exists purely so non-technical household members can type one memorable address; Google rejects `.rd` as an OAuth redirect domain, hence the split.

### k3s cluster
- Turion = server (control-plane), karenold = agent
- **Both nodes must use `--node-ip` pinned to their Tailscale IP** (`/etc/rancher/k3s/config.yaml`), not a local LAN address — otherwise the cluster breaks every time a node changes physical networks (see Gotchas). Turion additionally needs `flannel-iface: tailscale0` so the CNI layer looks on the right interface.
- Intended workload: parallel RL rollout workers for the Wizard project (`THE_WIZARD` repo) — CPU-bound environment simulation distributes well across weak nodes; GPU-bound training stays on whichever machine has the NVIDIA card.

## Certificates
Local HTTPS everywhere uses **mkcert**. The CA is per-machine (not portable) — when Turion died and came back, and when DaddyPC was wiped to become Aorus, each got a **fresh CA**, which means browsers need to re-trust the new root cert each time this happens. Root certs get distributed via `certutil -user -addstore -f Root` on Windows and manually via Keychain Access on macOS (cannot be done over SSH — needs a GUI session).

## Known gotchas (learned the hard way — read before touching networking or storage config)

1. **`/etc/fstab` entries for network/removable mounts need `nofail`.** Without it, a slow or unreachable mount at boot drops the whole machine into emergency mode. Aorus hit exactly this once.
2. **NTFS drives that survive an unclean shutdown often need the `force` mount option** (ntfs3 refuses to mount a "dirty" volume otherwise). Symptom: `nofail` lets boot succeed, but the drive silently isn't there, and a mergerfs pool built on top of it silently falls back to whatever empty placeholder directory is left.
3. **Home Assistant only reads `http:` YAML config once**, on first migration to its internal storage (`.storage/http`). Adding SSL settings to `configuration.yaml` *after* that first boot does nothing — you have to hand-edit `.storage/http`'s `stable` slot directly (stop the service first).
4. **Windows persistent drive mappings (`net use ... /persistent:yes`) only reconnect at the *next* interactive logon**, not live in the session that created them, and **never appear at all if created inside an elevated ("Run as Administrator") shell** — elevated processes get a different, invisible mapping bucket.
5. **k3s must be told its node's Tailscale IP explicitly** (`node-ip` + `flannel-iface` in `/etc/rancher/k3s/config.yaml`) if a node might ever change physical networks — otherwise it crash-loops with `failed to find interface with specified node ip`.
6. **`pkill -f` can kill its own shell** if the pattern you're searching for happens to appear in the command line that invoked `pkill` itself. Match on process name (`pkill -9 <name>`) instead of a broad `-f` pattern when unsure.
7. **`gsettings`/GNOME extension config changes made over SSH need the right `DBUS_SESSION_BUS_ADDRESS`**, pulled from an active `gnome-shell` process's environment (`/proc/<pid>/environ`) — there's no session context otherwise. Newly-installed GNOME extensions also don't activate until a full logout/login on Wayland.

## Pending / next steps
- Steve: mid-onboarding to Ubuntu Server + k3s (SSH key installed, Tailscale not yet joined as of this writing)
- karenold's Wi-Fi: was failing at the radio-authentication level for a long time (suspected loose antenna connector after the physical move) — resolved itself or was fixed manually; cause not fully confirmed
- LG ThinQ integration needs re-linking with a fresh Personal Access Token (the old one lived on the now-retired Turion instance)
- Litter-Robot / washer-dryer Home Assistant integrations not yet added on the new Aorus-hosted instance
- Home Assistant onboarding wizard status on Aorus should be double-checked
