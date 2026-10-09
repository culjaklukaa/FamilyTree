from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QMessageBox,
    QHeaderView, QTabWidget, QLabel, QFileDialog, QCheckBox
)
from PySide6.QtGui import QColor, QBrush, QAction
from family_tree_app.db import Database
from family_tree_app.repositories import PersonRepository, RelationshipRepository
from family_tree_app.ui.person_dialog import PersonDialog
from family_tree_app.ui.relationship_dialog import RelationshipDialog
from family_tree_app.ui.tree_view import TreeViewTab
from family_tree_app.ui.tree_view import TreeViewTab
from family_tree_app.ui.timeline_view import TimelineViewTab
from family_tree_app.ui.search_tab import SearchTab
from family_tree_app.gedcom_io import import_gedcom, export_gedcom
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()
        self.setWindowTitle("Family Tree App")
        self.resize(900, 600)
        self.db = db
        self.show_private_data = True  # owner sees everything by default
        self.person_repo = PersonRepository(db, enforce_privacy=not self.show_private_data)
        self.rel_repo = RelationshipRepository(db)
        
        self._create_menu()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # --- Tab widget ---
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # ========== People tab ==========
        self.people_tab = QWidget()
        self.people_layout = QVBoxLayout(self.people_tab)

        self.people_button_layout = QHBoxLayout()
        self.add_person_btn = QPushButton("Add Person")
        self.edit_person_btn = QPushButton("Edit Person")
        self.delete_person_btn = QPushButton("Delete Person")
        self.people_button_layout.addWidget(self.add_person_btn)
        self.people_button_layout.addWidget(self.edit_person_btn)
        self.people_button_layout.addWidget(self.delete_person_btn)
        self.people_layout.addLayout(self.people_button_layout)

        self.person_table = QTableWidget()
        self.person_table.setColumnCount(5)
        self.person_table.setHorizontalHeaderLabels(
            ["Name", "Birth Date", "Death Date", "Status", "ID"]
        )
        self.person_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.person_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.person_table.setSelectionMode(QTableWidget.SingleSelection)
        self.people_layout.addWidget(self.person_table)

        self.tabs.addTab(self.people_tab, "People")

        # ========== Relationships tab ==========
        self.rel_tab = QWidget()
        self.rel_layout = QVBoxLayout(self.rel_tab)

        self.rel_button_layout = QHBoxLayout()
        self.add_rel_btn = QPushButton("Add Relationship")
        self.edit_rel_btn = QPushButton("Edit Relationship")
        self.delete_rel_btn = QPushButton("Delete Relationship")
        self.rel_button_layout.addWidget(self.add_rel_btn)
        self.rel_button_layout.addWidget(self.edit_rel_btn)
        self.rel_button_layout.addWidget(self.delete_rel_btn)
        self.rel_layout.addLayout(self.rel_button_layout)

        self.rel_table = QTableWidget()
        self.rel_table.setColumnCount(6)
        self.rel_table.setHorizontalHeaderLabels(
            ["Person A", "Person B", "Type", "Dates", "Status", "ID"]
        )
        self.rel_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rel_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.rel_table.setSelectionMode(QTableWidget.SingleSelection)
        self.rel_layout.addWidget(self.rel_table)

        self.tabs.addTab(self.rel_tab, "Relationships")

        # ========== Tree View tab ==========
        self.tree_tab = TreeViewTab(self.person_repo, self.rel_repo)
        self.tabs.addTab(self.tree_tab, "Interactive Tree")

        # ========== Timeline View tab ==========
        self.timeline_tab = TimelineViewTab(self.person_repo, self.rel_repo)
        self.tabs.addTab(self.timeline_tab, "Timeline")

        # ========== Search tab ==========
        self.search_tab = SearchTab(self.person_repo, self)
        self.tabs.addTab(self.search_tab, "Search")

        # --- Signals ---
        self.add_person_btn.clicked.connect(self.add_person)
        self.edit_person_btn.clicked.connect(self.edit_person)
        self.delete_person_btn.clicked.connect(self.delete_person)

        self.add_rel_btn.clicked.connect(self.add_relationship)
        self.edit_rel_btn.clicked.connect(self.edit_relationship)
        self.delete_rel_btn.clicked.connect(self.delete_relationship)

        self.tree_tab.person_clicked.connect(self.open_person_from_tree)

        # Sync combo boxes
        self.tree_tab.root_person_combo.currentIndexChanged.connect(self._sync_tree_to_timeline)
        self.timeline_tab.filter_person_combo.currentIndexChanged.connect(self._sync_timeline_to_tree)

        # Initial data load
        self.refresh_people_table()
        self.refresh_rel_table()
        self.tree_tab.refresh_people_combo()
        self.timeline_tab.refresh_people_combo()
        # Setup auto-backup timer (checks every hour)
        from PySide6.QtCore import QTimer
        self.auto_backup_timer = QTimer(self)
        self.auto_backup_timer.timeout.connect(self.perform_auto_backup)
        self.auto_backup_timer.start(3600000) # 1 hour in milliseconds
        
        # Also run an initial check shortly after startup
        QTimer.singleShot(2000, self.perform_auto_backup)

    def perform_auto_backup(self):
        import datetime
        from family_tree_app.backup import create_backup
        
        last_backup_str = self.db.get_setting("last_backup_date")
        needs_backup = False
        
        if not last_backup_str:
            needs_backup = True
        else:
            try:
                last_backup = datetime.datetime.fromisoformat(last_backup_str)
                # Auto-backup if it's been more than 24 hours
                if (datetime.datetime.now() - last_backup).total_seconds() >= 86400:
                    needs_backup = True
            except ValueError:
                needs_backup = True
                
        if needs_backup:
            # Skip if database is completely empty
            if len(self.person_repo.get_all()) == 0:
                return
                
            try:
                # Perform silent backup to default location
                create_backup(self.db)
                self.db.set_setting("last_backup_date", datetime.datetime.now().isoformat())
                self.statusBar().showMessage("Automated backup successfully created.", 5000)
            except Exception as e:
                self.statusBar().showMessage(f"Automated backup failed: {str(e)}", 10000)

    def _sync_tree_to_timeline(self, index):
        person_id = self.tree_tab.root_person_combo.itemData(index)
        timeline_index = self.timeline_tab.filter_person_combo.findData(person_id)
        if timeline_index >= 0 and self.timeline_tab.filter_person_combo.currentIndex() != timeline_index:
            self.timeline_tab.filter_person_combo.setCurrentIndex(timeline_index)

    def _sync_timeline_to_tree(self, index):
        person_id = self.timeline_tab.filter_person_combo.itemData(index)
        if person_id:
            tree_index = self.tree_tab.root_person_combo.findData(person_id)
            if tree_index >= 0 and self.tree_tab.root_person_combo.currentIndex() != tree_index:
                self.tree_tab.root_person_combo.setCurrentIndex(tree_index)

    # ------------------------------------------------------------------
    # People helpers
    # ------------------------------------------------------------------
    def _person_name_map(self) -> dict:
        """Return {person_id: name} for display purposes."""
        return {p.id: p.name for p in self.person_repo.get_all()}

    def refresh_people_table(self):
        from family_tree_app.privacy import get_privacy_settings
        persons = self.person_repo.get_all()
        self.person_table.setColumnCount(6)
        self.person_table.setHorizontalHeaderLabels(
            ["Name", "Birth Date", "Death Date", "Privacy", "Status", "ID"]
        )
        self.person_table.setRowCount(len(persons))
        unverified_bg = QBrush(QColor(255, 243, 224))  # light orange
        private_bg = QBrush(QColor(230, 230, 250))  # light lavender
        for row, person in enumerate(persons):
            settings = get_privacy_settings(person)
            has_privacy = bool(settings)

            self.person_table.setItem(row, 0, QTableWidgetItem(person.name))
            self.person_table.setItem(
                row, 1, QTableWidgetItem(person.birth_date_str or "")
            )
            self.person_table.setItem(
                row, 2, QTableWidgetItem(person.death_date_str or "")
            )
            # Privacy indicator
            if settings.get("is_private"):
                priv_text = "🔒 Private"
            elif settings.get("is_living"):
                priv_text = "🔒 Living"
            elif has_privacy:
                priv_text = "🔒 Partial"
            else:
                priv_text = ""
            priv_item = QTableWidgetItem(priv_text)
            priv_item.setTextAlignment(Qt.AlignCenter)
            self.person_table.setItem(row, 3, priv_item)

            status_item = QTableWidgetItem("⚠ Unverified" if person.unverified else "✓")
            status_item.setTextAlignment(Qt.AlignCenter)
            self.person_table.setItem(row, 4, status_item)
            self.person_table.setItem(row, 5, QTableWidgetItem(person.id))
            # Row colouring
            if person.unverified:
                for col in range(self.person_table.columnCount()):
                    item = self.person_table.item(row, col)
                    if item:
                        item.setBackground(unverified_bg)
            elif has_privacy and not self.show_private_data:
                for col in range(self.person_table.columnCount()):
                    item = self.person_table.item(row, col)
                    if item:
                        item.setBackground(private_bg)
        self.person_table.setColumnHidden(5, True)

    def _selected_person_id(self):
        sel = self.person_table.selectedItems()
        if not sel:
            return None
        return self.person_table.item(sel[0].row(), 5).text()

    def add_person(self):
        dialog = PersonDialog(parent=self, db=self.db)
        if dialog.exec():
            self.person_repo.create(dialog.get_person())
            self.refresh_people_table()
            self.refresh_rel_table()  # names may appear in rel table
            self.tree_tab.refresh_people_combo()
            self.timeline_tab.refresh_people_combo()

    def edit_person(self):
        pid = self._selected_person_id()
        if not pid:
            QMessageBox.warning(self, "Select Person",
                                "Please select a person to edit.")
            return
        person = self.person_repo.get(pid)
        if not person:
            return
        if getattr(person, '_is_redacted', False):
            QMessageBox.warning(self, "Cannot Edit", 
                                "Cannot edit a private person while 'Show Private Data' is disabled.\nEnable it from the View menu first to edit.")
            return
            
        dialog = PersonDialog(parent=self, db=self.db, person=person)
        if dialog.exec():
            self.person_repo.update(dialog.get_person())
            self.refresh_people_table()
            self.refresh_rel_table()
            self.tree_tab.refresh_people_combo()
            self.timeline_tab.refresh_people_combo()

    def open_person_from_tree(self, person_id: str):
        """Open the detail/edit dialog for a person clicked in the tree view."""
        person = self.person_repo.get(person_id)
        if not person:
            return
        if getattr(person, '_is_redacted', False):
            QMessageBox.warning(self, "Cannot Edit", 
                                "Cannot view or edit a private person while 'Show Private Data' is disabled.\nEnable it from the View menu first.")
            return
            
        dialog = PersonDialog(parent=self, db=self.db, person=person)
        if dialog.exec():
            self.person_repo.update(dialog.get_person())
            self.refresh_people_table()
            self.refresh_rel_table()
            self.tree_tab.refresh_people_combo()
            self.timeline_tab.refresh_people_combo()

    def delete_person(self):
        pid = self._selected_person_id()
        if not pid:
            QMessageBox.warning(self, "Select Person",
                                "Please select a person to delete.")
            return
        # Check for existing relationships
        rels = self.rel_repo.get_by_person(pid)
        msg = "Are you sure you want to delete this person?"
        if rels:
            msg += (f"\n\nThis person is part of {len(rels)} relationship(s) "
                    "which will also be deleted.")
        reply = QMessageBox.question(
            self, "Confirm Delete", msg,
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # Delete associated relationships first
            for rel in rels:
                self.rel_repo.delete(rel.id)
            self.person_repo.delete(pid)
            self.refresh_people_table()
            self.refresh_rel_table()
            self.tree_tab.refresh_people_combo()
            self.timeline_tab.refresh_people_combo()

    # ------------------------------------------------------------------
    # Relationship helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _format_rel_type(type_key: str) -> str:
        """Turn 'parent-child:biological' into 'Parent–Child (Biological)'."""
        from family_tree_app.ui.relationship_dialog import ALL_RELATIONSHIP_TYPES
        for key, label in ALL_RELATIONSHIP_TYPES:
            if key == type_key:
                return label
        return type_key  # fallback: show raw key

    @staticmethod
    def _format_rel_dates(rel) -> str:
        parts = []
        if rel.start_date_str:
            parts.append(f"from {rel.start_date_str}")
        if rel.end_date_str:
            parts.append(f"to {rel.end_date_str}")
        return " ".join(parts)

    def refresh_rel_table(self):
        persons = self.person_repo.get_all()
        name_map = {p.id: p.name for p in persons}
        # Gather all relationships (deduplicate via a set of IDs)
        seen = set()
        all_rels = []
        for p in persons:
            for r in self.rel_repo.get_by_person(p.id):
                if r.id not in seen:
                    seen.add(r.id)
                    all_rels.append(r)

        from family_tree_app.siblings import derive_siblings
        derived_sibs = derive_siblings(all_rels)

        self.rel_table.setRowCount(len(all_rels) + len(derived_sibs))
        unverified_bg = QBrush(QColor(255, 243, 224))  # light orange
        
        row = 0
        for rel in all_rels:
            self.rel_table.setItem(
                row, 0,
                QTableWidgetItem(name_map.get(rel.person_a_id, rel.person_a_id))
            )
            self.rel_table.setItem(
                row, 1,
                QTableWidgetItem(name_map.get(rel.person_b_id, rel.person_b_id))
            )
            self.rel_table.setItem(
                row, 2, QTableWidgetItem(self._format_rel_type(rel.type))
            )
            self.rel_table.setItem(
                row, 3, QTableWidgetItem(self._format_rel_dates(rel))
            )
            status_item = QTableWidgetItem("⚠ Unverified" if rel.unverified else "✓")
            status_item.setTextAlignment(Qt.AlignCenter)
            self.rel_table.setItem(row, 4, status_item)
            self.rel_table.setItem(row, 5, QTableWidgetItem(rel.id))
            if rel.unverified:
                for col in range(self.rel_table.columnCount()):
                    item = self.rel_table.item(row, col)
                    if item:
                        item.setBackground(unverified_bg)
            row += 1
            
        for sib in derived_sibs:
            self.rel_table.setItem(
                row, 0,
                QTableWidgetItem(name_map.get(sib.person_a_id, sib.person_a_id))
            )
            self.rel_table.setItem(
                row, 1,
                QTableWidgetItem(name_map.get(sib.person_b_id, sib.person_b_id))
            )
            type_label = sib.kind.replace("-", " ").title() + " (Derived)"
            self.rel_table.setItem(
                row, 2, QTableWidgetItem(type_label)
            )
            self.rel_table.setItem(
                row, 3, QTableWidgetItem("-")
            )
            self.rel_table.setItem(row, 4, QTableWidgetItem("-"))
            self.rel_table.setItem(row, 5, QTableWidgetItem("DERIVED"))
            row += 1

        self.rel_table.setColumnHidden(5, True)

    def _selected_rel_id(self):
        sel = self.rel_table.selectedItems()
        if not sel:
            return None
        return self.rel_table.item(sel[0].row(), 5).text()

    def add_relationship(self):
        persons = self.person_repo.get_all()
        if len(persons) < 2:
            QMessageBox.warning(
                self, "Not Enough People",
                "You need at least two people before creating a relationship."
            )
            return
        dialog = RelationshipDialog(self, persons=persons)
        if dialog.exec():
            self.rel_repo.create(dialog.get_relationship())
            self.refresh_rel_table()
            self.tree_tab.clear_cache()
            self.tree_tab.draw_tree()
            self.timeline_tab.refresh_timeline()

    def edit_relationship(self):
        rid = self._selected_rel_id()
        if not rid:
            QMessageBox.warning(self, "Select Relationship",
                                "Please select a relationship to edit.")
            return
        if rid == "DERIVED":
            QMessageBox.information(self, "Derived Relationship",
                                "This relationship is computed from parent links and cannot be edited directly.")
            return
            
        rel = self.rel_repo.get(rid)
        if not rel:
            return
        persons = self.person_repo.get_all()
        dialog = RelationshipDialog(self, persons=persons, relationship=rel)
        if dialog.exec():
            self.rel_repo.update(dialog.get_relationship())
            self.refresh_rel_table()
            self.tree_tab.clear_cache()
            self.tree_tab.draw_tree()
            self.timeline_tab.refresh_timeline()

    def delete_relationship(self):
        rid = self._selected_rel_id()
        if not rid:
            QMessageBox.warning(self, "Select Relationship",
                                "Please select a relationship to delete.")
            return
        if rid == "DERIVED":
            QMessageBox.information(self, "Derived Relationship",
                                "This relationship is computed from parent links and cannot be deleted directly. Delete the parent link instead.")
            return
            
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this relationship?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.rel_repo.delete(rid)
            self.refresh_rel_table()
            self.tree_tab.clear_cache()
            self.tree_tab.draw_tree()
            self.timeline_tab.refresh_timeline()

    def _create_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        import_action = QAction("Import GEDCOM...", self)
        import_action.triggered.connect(self.action_import_gedcom)
        file_menu.addAction(import_action)

        export_action = QAction("Export GEDCOM...", self)
        export_action.triggered.connect(self.action_export_gedcom)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        backup_action = QAction("Create Backup...", self)
        backup_action.triggered.connect(self.action_create_backup)
        file_menu.addAction(backup_action)

        # --- View menu ---
        view_menu = menu_bar.addMenu("&View")

        self.toggle_privacy_action = QAction("Show Private Data", self)
        self.toggle_privacy_action.setCheckable(True)
        self.toggle_privacy_action.setChecked(True)
        self.toggle_privacy_action.toggled.connect(self._on_privacy_toggled)
        view_menu.addAction(self.toggle_privacy_action)

    def _on_privacy_toggled(self, checked: bool):
        self.show_private_data = checked
        self.person_repo.enforce_privacy = not checked
        self.refresh_people_table()
        self.refresh_rel_table()
        self.tree_tab.show_private_data = checked
        self.tree_tab.refresh_people_combo()
        self.tree_tab.clear_cache()
        self.tree_tab.draw_tree()
        self.timeline_tab.show_private_data = checked
        self.timeline_tab.refresh_people_combo()
        self.timeline_tab.refresh_timeline()
        self.search_tab.perform_search()

    def action_import_gedcom(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import GEDCOM", "", "GEDCOM Files (*.ged);;All Files (*)"
        )
        if file_path:
            try:
                persons_added, rels_added = import_gedcom(file_path, self.db)
                QMessageBox.information(
                    self, "Import Successful",
                    f"Imported {persons_added} persons and {rels_added} relationships."
                )
                self.refresh_people_table()
                self.refresh_rel_table()
                self.tree_tab.refresh_people_combo()
                self.tree_tab.clear_cache()
                self.tree_tab.draw_tree()
                self.timeline_tab.refresh_people_combo()
                self.timeline_tab.refresh_timeline()
            except Exception as e:
                QMessageBox.critical(self, "Import Failed", f"An error occurred during import:\n{str(e)}")

    def action_export_gedcom(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export GEDCOM", "", "GEDCOM Files (*.ged);;All Files (*)"
        )
        if file_path:
            reply = QMessageBox.question(
                self, "Privacy Settings",
                "Do you want to apply privacy settings and redact private data in this export?\n\n"
                "Click Yes to redact, No to export all data as-is.",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Cancel:
                return
            force_public = (reply == QMessageBox.No)
            try:
                persons_exported, rels_exported = export_gedcom(file_path, self.db, force_public=force_public)
                QMessageBox.information(
                    self, "Export Successful",
                    f"Exported {persons_exported} persons and {rels_exported} relationships."
                )
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"An error occurred during export:\n{str(e)}")

    def action_create_backup(self):
        from family_tree_app.backup import create_backup
        
        # Prompt user for save location
        timestamp = __import__("datetime").datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = f"FamilyTreeApp_Backup_{timestamp}.zip"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Backup", default_name, "ZIP Archives (*.zip);;All Files (*)"
        )
        
        if file_path:
            try:
                final_path = create_backup(self.db, output_path=file_path)
                # Record successful backup time
                self.db.set_setting("last_backup_date", __import__("datetime").datetime.now().isoformat())
                QMessageBox.information(
                    self, "Backup Successful",
                    f"Backup successfully created at:\n{final_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Backup Failed", f"An error occurred during backup:\n{str(e)}")
