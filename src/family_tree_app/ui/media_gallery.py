from pathlib import Path
import uuid
import shutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem, QFileDialog, QProgressDialog, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QImage

from family_tree_app.models import Media
from family_tree_app.repositories import MediaRepository
from family_tree_app.db import Database

import os
import mimetypes

class MediaProcessorThread(QThread):
    finished_processing = Signal(Media, str) # media_model, error_string
    progress_update = Signal(str)

    def __init__(self, file_paths, db: Database, media_repo, person_id=None, event_id=None):
        super().__init__()
        self.file_paths = file_paths
        self.db = db
        self.media_repo = media_repo
        self.person_id = person_id
        self.event_id = event_id

    def run(self):
        media_dir = self.db.media_dir
        thumb_dir = self.db.thumbnail_dir
        media_dir.mkdir(parents=True, exist_ok=True)
        thumb_dir.mkdir(parents=True, exist_ok=True)

        for fp in self.file_paths:
            source_path = Path(fp)
            if not source_path.exists():
                continue
                
            self.progress_update.emit(f"Processing {source_path.name}...")

            # Generate unique name
            ext = source_path.suffix
            new_filename = f"{uuid.uuid4().hex}{ext}"
            dest_path = media_dir / new_filename
            thumb_path = thumb_dir / f"thumb_{new_filename}"

            try:
                # Copy file
                shutil.copy2(source_path, dest_path)
                file_size = dest_path.stat().st_size
                mime_type, _ = mimetypes.guess_type(str(dest_path))

                # Generate thumbnail if it's an image
                image = QImage(str(dest_path))
                if not image.isNull():
                    thumb_img = image.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    thumb_img.save(str(thumb_path))
                
                # Create Media record
                media = Media(
                    file_path=str(dest_path.relative_to(self.db.data_dir)),
                    thumbnail_path=str(thumb_path.relative_to(self.db.data_dir)) if not image.isNull() else None,
                    title=source_path.name,
                    mime_type=mime_type,
                    file_size=file_size,
                    person_id=self.person_id,
                    event_id=self.event_id
                )
                
                # Save to repo
                created = self.media_repo.create(media)
                self.finished_processing.emit(created, "")
            except Exception as e:
                self.finished_processing.emit(Media(file_path=""), str(e))

class MediaGalleryWidget(QWidget):
    def __init__(self, db: Database, person_id: str = None, event_id: str = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.media_repo = MediaRepository(db)
        self.person_id = person_id
        self.event_id = event_id
        
        self.layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setIconSize(QSize(150, 150))
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSpacing(10)
        
        self.add_button = QPushButton("Add Media...")
        self.add_button.clicked.connect(self.add_media)
        
        self.layout.addWidget(self.add_button)
        self.layout.addWidget(self.list_widget)
        
        self.load_media()
        
    def load_media(self):
        self.list_widget.clear()
        if self.person_id:
            media_items = self.media_repo.get_by_person(self.person_id)
        elif self.event_id:
            media_items = self.media_repo.get_by_event(self.event_id)
        else:
            return
            
        for media in media_items:
            self.add_media_to_view(media)
            
    def add_media_to_view(self, media: Media):
        item = QListWidgetItem(media.title or "Untitled")
        item.setData(Qt.UserRole, media)
        
        if media.thumbnail_path:
            full_thumb_path = self.db.data_dir / media.thumbnail_path
            if full_thumb_path.exists():
                item.setIcon(QIcon(str(full_thumb_path)))
        else:
            full_path = self.db.data_dir / media.file_path
            if full_path.exists():
                item.setIcon(QIcon(str(full_path)))
                
        self.list_widget.addItem(item)
        
    def add_media(self):
        if not self.person_id and not self.event_id:
            QMessageBox.warning(self, "Cannot Add Media", "Please save the person or event before adding media.")
            return

        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Media", "", "Images (*.png *.xpm *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        if not file_paths:
            return
            
        self.processor = MediaProcessorThread(
            file_paths, self.db, self.media_repo, self.person_id, self.event_id
        )
        self.processor.finished_processing.connect(self.on_media_processed)
        self.processor.start()
        
    def on_media_processed(self, media: Media, error: str):
        if error:
            QMessageBox.critical(self, "Error", f"Failed to process media: {error}")
            return
        if media and media.file_path:
            self.add_media_to_view(media)
