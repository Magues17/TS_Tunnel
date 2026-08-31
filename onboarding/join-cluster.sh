#!/usr/bin/env bash
# Run this on any Linux or macOS machine joining the cluster.
# Idempotent - safe to re-run. Needs sudo for the SSH server step.
set -e

PUBKEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFZiBsO0zAT8DnW0VpASr2ss2grPj8zjkkjCjGmMU8/n msi-cluster-control"

echo "=== Enabling SSH server ==="
if [ "$(uname)" = "Darwin" ]; then
    sudo systemsetup -setremotelogin on
else
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update -y
        sudo apt-get install -y openssh-server
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y openssh-server
    fi
    sudo systemctl enable --now ssh 2>/dev/null || sudo systemctl enable --now sshd
fi

echo "=== Installing cluster key ==="
mkdir -p ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
if ! grep -qF "$PUBKEY" ~/.ssh/authorized_keys; then
    echo "$PUBKEY" >> ~/.ssh/authorized_keys
fi
chmod 600 ~/.ssh/authorized_keys

echo "=== Creating 4KLABS folder ==="
mkdir -p ~/4KLABS

echo ""
echo "=== DONE. Send these back for SSH config: ==="
echo "Hostname: $(hostname)"
echo "Username: $(whoami)"
