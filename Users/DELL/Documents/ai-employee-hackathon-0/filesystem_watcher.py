from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import shutil
import time

VAULT_PATH = r"C:\Users\DELL\Documents\AI_Employee_Vault"

class DropFolderHandler(FileSystemEventHandler):
    def __init__(self, vault_path):
        super().__init__()
        self.needs_action = Path(vault_path) / 'Needs_Action'
        self.processed = set()

    def on_modified(self, event):
        if event.is_directory:
            return
        self.process_file(Path(event.src_path))

    def on_created(self, event):
        if event.is_directory:
            return
        time.sleep(2)
        self.process_file(Path(event.src_path))

    def process_file(self, source):
        if source in self.processed:
            return
        if not source.exists():
            return
        try:
            self.processed.add(source)
            dest = self.needs_action / f'FILE_{source.name}'
            shutil.copy2(source, dest)
            meta_path = self.needs_action / f'FILE_{source.stem}.md'
            meta_path.write_text(
                f'---\ntype: file_drop\noriginal_name: {source.name}\n---\n'
                f'# New File Received: {source.name}\n\n'
                f'## Suggested Actions\n- [ ] Process this file\n- [ ] Move to Done when complete\n'
            )
            print(f"New file detected: {source.name}")
        except Exception as e:
            print(f"Error: {e}")

DROP_FOLDER = r"C:\Users\DELL\Desktop\drop_here"
Path(DROP_FOLDER).mkdir(exist_ok=True)

handler = DropFolderHandler(VAULT_PATH)
observer = Observer()
observer.schedule(handler, DROP_FOLDER, recursive=False)
observer.start()
print(f"Watching folder: {DROP_FOLDER}")
print("Drop any file in 'drop_here' folder on Desktop to test...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()