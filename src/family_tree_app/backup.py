import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from family_tree_app.db import Database

def create_backup(db: Database, output_path: str | Path = None) -> Path:
    """
    Creates a zip archive of the entire data directory (DB + media).
    If output_path is None, saves it to a default 'backups' folder in the cwd
    with a timestamped filename.
    Returns the path to the created zip file.
    """
    data_dir = db.data_dir
    if str(db.db_path) == ":memory:":
        raise ValueError("Cannot backup an in-memory database.")
        
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory {data_dir} does not exist.")
        
    if output_path is None:
        backup_dir = Path.cwd() / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        archive_name = f"FamilyTreeApp_Backup_{timestamp}.zip"
        archive_path = backup_dir / archive_name
    else:
        archive_path = Path(output_path)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(data_dir):
            for file in files:
                file_path = Path(root) / file
                # Calculate path relative to the parent of data_dir
                # So inside the zip, it looks like 'data/family_tree.db'
                arcname = file_path.relative_to(data_dir.parent)
                zipf.write(file_path, arcname)
                
    return archive_path
