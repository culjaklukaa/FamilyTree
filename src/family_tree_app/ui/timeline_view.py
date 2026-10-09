from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush

from family_tree_app.repositories import PersonRepository, RelationshipRepository
from family_tree_app.models import Event

class TimelineViewTab(QWidget):
    person_clicked = Signal(str)

    def __init__(self, person_repo: PersonRepository, rel_repo: RelationshipRepository):
        super().__init__()
        self.person_repo = person_repo
        self.rel_repo = rel_repo
        self.show_private_data = True
        
        self._main_layout = QVBoxLayout(self)
        
        # --- Toolbar ---
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Filter by Person:"))
        self.filter_person_combo = QComboBox()
        toolbar.addWidget(self.filter_person_combo)
        toolbar.addStretch()
        self._main_layout.addLayout(toolbar)
        
        # --- Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Date", "Type", "Description", "Place", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self._main_layout.addWidget(self.table)
        
        self.filter_person_combo.currentIndexChanged.connect(self._on_filter_changed)
        
    def refresh_people_combo(self):
        # Save current selection
        current_id = self.filter_person_combo.currentData()
        
        self.filter_person_combo.blockSignals(True)
        self.filter_person_combo.clear()
        self.filter_person_combo.addItem("All People", None)
        for p in self.person_repo.get_all():
            self.filter_person_combo.addItem(p.name, p.id)
            
        # Restore selection
        if current_id:
            idx = self.filter_person_combo.findData(current_id)
            if idx >= 0:
                self.filter_person_combo.setCurrentIndex(idx)
                
        self.filter_person_combo.blockSignals(False)
        self.refresh_timeline()

    def _on_filter_changed(self):
        self.refresh_timeline()
        
    def _gather_events(self):
        events = []
        people = {p.id: p for p in self.person_repo.get_all()}
        
        for p in people.values():
            if p.birth_date or p.birth_date_str:
                events.append(Event(
                    type="birth",
                    date=p.birth_date,
                    date_str=p.birth_date_str,
                    place=p.birth_place,
                    description=f"Birth of {p.name}",
                    person_id=p.id,
                    unverified=p.unverified
                ))
            if p.death_date or p.death_date_str:
                events.append(Event(
                    type="death",
                    date=p.death_date,
                    date_str=p.death_date_str,
                    place=p.death_place,
                    description=f"Death of {p.name}",
                    person_id=p.id,
                    unverified=p.unverified
                ))
                
        # Gather relationships
        for p in people.values():
            for r in self.rel_repo.get_by_person(p.id):
                # Only process once per relationship
                if p.id != r.person_a_id: 
                    continue
                a_name = people[r.person_a_id].name if r.person_a_id in people else "?"
                b_name = people[r.person_b_id].name if r.person_b_id in people else "?"
                if r.start_date or r.start_date_str:
                    events.append(Event(
                        type=f"{r.type} start",
                        date=r.start_date,
                        date_str=r.start_date_str,
                        description=f"{r.type.title()} started between {a_name} and {b_name}",
                        relationship_id=r.id,
                        person_id=r.person_a_id, # associate with person A for filtering
                        unverified=r.unverified
                    ))
                if r.end_date or r.end_date_str:
                    events.append(Event(
                        type=f"{r.type} end",
                        date=r.end_date,
                        date_str=r.end_date_str,
                        description=f"{r.type.title()} ended between {a_name} and {b_name}",
                        relationship_id=r.id,
                        person_id=r.person_a_id,
                        unverified=r.unverified
                    ))
        return events
        
    def refresh_timeline(self):
        events = self._gather_events()
        
        # Filter
        filter_id = self.filter_person_combo.currentData()
        if filter_id:
            filtered = []
            for e in events:
                if e.person_id == filter_id:
                    filtered.append(e)
                elif e.relationship_id:
                    # check if the relationship involves this person
                    rel = self.rel_repo.get(e.relationship_id)
                    if rel and (rel.person_a_id == filter_id or rel.person_b_id == filter_id):
                        filtered.append(e)
            events = filtered
            
        # Sort chronologically. 
        # Fallbacks: date > date_str > ''
        events.sort(key=lambda e: e.date or e.date_str or "")
        
        self.table.setRowCount(len(events))
        unverified_bg = QBrush(QColor(255, 243, 224))  # light orange
        for row, e in enumerate(events):
            display_date = e.date_str if e.date_str else (e.date if e.date else "Unknown")
            self.table.setItem(row, 0, QTableWidgetItem(display_date))
            self.table.setItem(row, 1, QTableWidgetItem(e.type.title()))
            self.table.setItem(row, 2, QTableWidgetItem(e.description or ""))
            self.table.setItem(row, 3, QTableWidgetItem(e.place or ""))
            status_item = QTableWidgetItem("⚠ Unverified" if e.unverified else "✓")
            status_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, status_item)
            if e.unverified:
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(unverified_bg)
