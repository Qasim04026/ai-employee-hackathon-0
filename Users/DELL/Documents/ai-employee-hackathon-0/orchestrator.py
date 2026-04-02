import subprocess
import time
from pathlib import Path

VAULT_PATH = r"C:\Users\DELL\Documents\AI_Employee_Vault"

processes = {
    'gmail_watcher': ['python', 'gmail_watcher.py'],
    'file_watcher': ['python', 'filesystem_watcher.py'],
}

running = {}

def start_all():
    for name, cmd in processes.items():
        print(f"Starting {name}...")
        running[name] = subprocess.Popen(cmd)
        time.sleep(2)

def monitor():
    print("All watchers running. Press Ctrl+C to stop.")
    while True:
        for name, proc in list(running.items()):
            if proc.poll() is not None:
                print(f"{name} crashed! Restarting...")
                running[name] = subprocess.Popen(processes[name])
        time.sleep(30)

start_all()
monitor()