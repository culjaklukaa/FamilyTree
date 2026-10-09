import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
    QTextEdit, QDialogButtonBox, QCheckBox, QTabWidget, QWidget,
    QGroupBox, QLabel
)
from family_tree_app.models import Person
from family_tree_app.db import Database
from family_tree_app.ui.media_gallery import MediaGalleryWidget
from family_tree_app.ui.sources_widget import SourcesWidget

class PersonDialog(QDialog):
    def __init__(self, parent=None, db: Database = None, person: Person = None):
        super().__init__(parent)
        self.setWindowTitle("Person Details")
        self.person_id = person.id if person else None
        self.db = db
        
        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        # Details Tab
        self.details_tab = QWidget()
        self.form_layout = QFormLayout(self.details_tab)
        
        self.first_name_input = QLineEdit()
        self.last_name_input = QLineEdit()
        self.maiden_name_input = QLineEdit()
        self.nicknames_input = QLineEdit()
        
        self.birth_date_input = QLineEdit()
        self.birth_place_input = QLineEdit()
        
        self.is_deceased_checkbox = QCheckBox("Is Deceased")
        self.is_deceased_checkbox.toggled.connect(self._on_deceased_toggled)
        
        self.death_date_input = QLineEdit()
        self.death_place_input = QLineEdit()
        
        self.photo_path_input = QLineEdit()
        self.occupation_input = QLineEdit()
        self.notes_input = QTextEdit()
        self.custom_fields_input = QTextEdit()
        self.unverified_checkbox = QCheckBox("Unverified")
        
        self.form_layout.addRow("First Name*", self.first_name_input)
        self.form_layout.addRow("Last Name*", self.last_name_input)
        self.form_layout.addRow("Maiden Name", self.maiden_name_input)
        self.form_layout.addRow("Nicknames", self.nicknames_input)
        
        self.form_layout.addRow("Birth Date (YYYY-MM-DD)", self.birth_date_input)
        self.form_layout.addRow("Birth Place", self.birth_place_input)
        
        self.form_layout.addRow("", self.is_deceased_checkbox)
        
        self.form_layout.addRow("Death Date (YYYY-MM-DD)", self.death_date_input)
        self.form_layout.addRow("Death Place", self.death_place_input)
        
        self.form_layout.addRow("Photo Path", self.photo_path_input)
        self.form_layout.addRow("Occupation", self.occupation_input)
        self.form_layout.addRow("Notes", self.notes_input)
        self.form_layout.addRow("Custom Fields (JSON)", self.custom_fields_input)
        self.form_layout.addRow("", self.unverified_checkbox)
        
        self._on_deceased_toggled(False)
        
        self.tabs.addTab(self.details_tab, "Details")
        
        # Privacy Tab
        self._create_privacy_tab()
        
        if self.db and self.person_id:
            self.media_tab = MediaGalleryWidget(db=self.db, person_id=self.person_id)
            self.tabs.addTab(self.media_tab, "Media")
            self.sources_tab = SourcesWidget(db=self.db, person_id=self.person_id)
            self.tabs.addTab(self.sources_tab, "Sources")
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
        
        if person:
            self.populate_fields(person)

    def _create_privacy_tab(self):
        """Build the Privacy tab with person-level and field-level controls."""
        self.privacy_tab = QWidget()
        privacy_layout = QVBoxLayout(self.privacy_tab)

        # --- Person-level privacy ---
        person_group = QGroupBox("Person-Level Privacy")
        person_group_layout = QVBoxLayout(person_group)
        self.privacy_private_cb = QCheckBox("Mark as Private (hide all details in exports and views)")
        self.privacy_living_cb = QCheckBox("Mark as Living (redact details, show as \"Living\")")
        person_group_layout.addWidget(self.privacy_private_cb)
        person_group_layout.addWidget(self.privacy_living_cb)
        privacy_layout.addWidget(person_group)

        # Make them mutually exclusive
        self.privacy_private_cb.toggled.connect(
            lambda checked: self.privacy_living_cb.setChecked(False) if checked else None
        )
        self.privacy_living_cb.toggled.connect(
            lambda checked: self.privacy_private_cb.setChecked(False) if checked else None
        )

        # --- Field-level privacy ---
        field_group = QGroupBox("Field-Level Privacy (hide individual fields)")
        field_group_layout = QVBoxLayout(field_group)
        self.privacy_hide_notes_cb = QCheckBox("Hide Notes")
        self.privacy_hide_birth_cb = QCheckBox("Hide Birth Details")
        self.privacy_hide_death_cb = QCheckBox("Hide Death Details")
        self.privacy_hide_occupation_cb = QCheckBox("Hide Occupation")
        self.privacy_hide_photo_cb = QCheckBox("Hide Photo")
        field_group_layout.addWidget(self.privacy_hide_notes_cb)
        field_group_layout.addWidget(self.privacy_hide_birth_cb)
        field_group_layout.addWidget(self.privacy_hide_death_cb)
        field_group_layout.addWidget(self.privacy_hide_occupation_cb)
        field_group_layout.addWidget(self.privacy_hide_photo_cb)
        privacy_layout.addWidget(field_group)

        privacy_layout.addWidget(QLabel(
            "Note: Privacy settings control what is shown in exports and\n"
            "when \"Show Private Data\" is turned off in the main window."
        ))
        privacy_layout.addStretch()
        self.tabs.addTab(self.privacy_tab, "Privacy")

    def _on_deceased_toggled(self, checked: bool):
        self.death_date_input.setVisible(checked)
        self.death_place_input.setVisible(checked)
        
        label = self.form_layout.labelForField(self.death_date_input)
        if label: label.setVisible(checked)
        
        label2 = self.form_layout.labelForField(self.death_place_input)
        if label2: label2.setVisible(checked)

    def populate_fields(self, person: Person):
        full_name = person.name or ""
        parts = full_name.rsplit(" ", 1)
        if len(parts) == 2:
            self.first_name_input.setText(parts[0])
            self.last_name_input.setText(parts[1])
        else:
            self.first_name_input.setText(full_name)
            self.last_name_input.setText("")
            
        self.maiden_name_input.setText(person.maiden_name or "")
        self.nicknames_input.setText(person.nicknames or "")
        self.birth_date_input.setText(person.birth_date or "")
        self.birth_place_input.setText(person.birth_place or "")
        self.death_date_input.setText(person.death_date or "")
        self.death_place_input.setText(person.death_place or "")
        
        if person.death_date or person.death_place:
            self.is_deceased_checkbox.setChecked(True)
        else:
            self.is_deceased_checkbox.setChecked(False)
        self._on_deceased_toggled(self.is_deceased_checkbox.isChecked())
        
        self.photo_path_input.setText(person.photo_path or "")
        self.occupation_input.setText(person.occupation or "")
        self.notes_input.setPlainText(person.notes or "")
        self.custom_fields_input.setPlainText(person.custom_fields or "")
        self.unverified_checkbox.setChecked(person.unverified)
        self._populate_privacy(person)

    def _populate_privacy(self, person: Person):
        """Load privacy_settings JSON into checkboxes."""
        settings = {}
        if person.privacy_settings:
            try:
                settings = json.loads(person.privacy_settings)
            except json.JSONDecodeError:
                pass
        self.privacy_private_cb.setChecked(settings.get("is_private", False))
        self.privacy_living_cb.setChecked(settings.get("is_living", False))
        self.privacy_hide_notes_cb.setChecked(settings.get("hide_notes", False))
        self.privacy_hide_birth_cb.setChecked(settings.get("hide_birth", False))
        self.privacy_hide_death_cb.setChecked(settings.get("hide_death", False))
        hidden_fields = settings.get("hidden_fields", [])
        self.privacy_hide_occupation_cb.setChecked("occupation" in hidden_fields)
        self.privacy_hide_photo_cb.setChecked("photo_path" in hidden_fields)

    def _build_privacy_settings(self) -> str | None:
        """Serialize checkboxes into a JSON string (or None if all off)."""
        settings = {}
        if self.privacy_private_cb.isChecked():
            settings["is_private"] = True
        if self.privacy_living_cb.isChecked():
            settings["is_living"] = True
        if self.privacy_hide_notes_cb.isChecked():
            settings["hide_notes"] = True
        if self.privacy_hide_birth_cb.isChecked():
            settings["hide_birth"] = True
        if self.privacy_hide_death_cb.isChecked():
            settings["hide_death"] = True
        hidden_fields = []
        if self.privacy_hide_occupation_cb.isChecked():
            hidden_fields.append("occupation")
        if self.privacy_hide_photo_cb.isChecked():
            hidden_fields.append("photo_path")
        if hidden_fields:
            settings["hidden_fields"] = hidden_fields
        if not settings:
            return None
        return json.dumps(settings)
        
    def get_person(self) -> Person:
        first = self.first_name_input.text().strip()
        last = self.last_name_input.text().strip()
        name = f"{first} {last}".strip()
        
        maiden = self.maiden_name_input.text().strip()
        if not maiden and last:
            maiden = last

        death_date = self.death_date_input.text() or None if self.is_deceased_checkbox.isChecked() else None
        death_place = self.death_place_input.text() or None if self.is_deceased_checkbox.isChecked() else None

        kwargs = {
            "name": name,
            "maiden_name": maiden or None,
            "nicknames": self.nicknames_input.text() or None,
            "birth_date_str": None,
            "birth_date": self.birth_date_input.text() or None,
            "birth_place": self.birth_place_input.text() or None,
            "death_date_str": None,
            "death_date": death_date,
            "death_place": death_place,
            "photo_path": self.photo_path_input.text() or None,
            "occupation": self.occupation_input.text() or None,
            "notes": self.notes_input.toPlainText() or None,
            "custom_fields": self.custom_fields_input.toPlainText() or None,
            "privacy_settings": self._build_privacy_settings(),
            "unverified": self.unverified_checkbox.isChecked()
        }
        if self.person_id:
            kwargs["id"] = self.person_id
            
        return Person(**kwargs)

    def accept(self):
        if not self.first_name_input.text().strip() and not self.last_name_input.text().strip():
            # Minimal validation - name is required
            return
        super().accept()
