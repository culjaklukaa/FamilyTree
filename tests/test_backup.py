import os
import zipfile
from pathlib import Path
from family_tree_app.db import Database
from family_tree_app.backup import create_backup

def test_create_backup(tmp_path):
    # Setup dummy database and data directory
    db_path = tmp_path / "data" / "test.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = Database(db_path)
    
    # Create some dummy files in the data directory
    (db.data_dir / "media").mkdir(parents=True, exist_ok=True)
    (db.data_dir / "test.db").touch()
    (db.data_dir / "media" / "photo.jpg").touch()
    
    # Test backup creation
    backup_path = tmp_path / "test_backup.zip"
    result_path = create_backup(db, output_path=backup_path)
    
    assert result_path == backup_path
    assert result_path.exists()
    
    # Verify zip contents
    with zipfile.ZipFile(result_path, 'r') as zipf:
        contents = zipf.namelist()
        # The paths inside the zip should start with 'data/'
        assert "data/test.db" in [c.replace("\\", "/") for c in contents]
        assert "data/media/photo.jpg" in [c.replace("\\", "/") for c in contents]

def test_create_backup_default_path(tmp_path, monkeypatch):
    # Setup dummy database
    db_path = tmp_path / "data" / "test.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = Database(db_path)
    (db.data_dir / "test.db").touch()
    
    # Mock current working directory to tmp_path
    monkeypatch.chdir(tmp_path)
    
    # Call without output path
    result_path = create_backup(db)
    
    assert result_path.parent == tmp_path / "backups"
    assert result_path.name.startswith("FamilyTreeApp_Backup_")
    assert result_path.name.endswith(".zip")
    assert result_path.exists()
