"""Runs commands on fleet machines over SSH using the shared cluster_key."""
import paramiko

KEY_PATH = "/home/mikel/.ssh/panel_key"


def run(host, user, command, timeout=30):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        if host == "localhost":
            client.connect(hostname="localhost", username=user, key_filename=KEY_PATH, timeout=timeout)
        else:
            client.connect(hostname=host, username=user, key_filename=KEY_PATH, timeout=timeout)
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        code = stdout.channel.recv_exit_status()
        return {"ok": code == 0, "stdout": out, "stderr": err, "exit_code": code}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "exit_code": -1}
    finally:
        client.close()
