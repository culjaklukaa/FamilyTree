from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from family_tree_app.repositories import PersonRepository

class SearchTab(QWidget):
    def __init__(self, person_repo: PersonRepository, main_window):
        super().__init__()
        self.person_repo = person_repo
        self.main_window = main_window
        
        self.layout = QVBoxLayout(self)
        
        # --- Search Inputs ---
        self.input_layout = QHBoxLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Search by name or nickname...")
        self.input_layout.addWidget(QLabel("Name:"))
        self.input_layout.addWidget(self.name_input)
        
        self.birth_place_input = QLineEdit()
        self.birth_place_input.setPlaceholderText("Search by birthplace...")
        self.input_layout.addWidget(QLabel("Birthplace:"))
        self.input_layout.addWidget(self.birth_place_input)
        
        self.birth_date_from = QLineEdit()
        self.birth_date_from.setPlaceholderText("YYYY-MM-DD")
        self.input_layout.addWidget(QLabel("Born From:"))
        self.input_layout.addWidget(self.birth_date_from)
        
        self.birth_date_to = QLineEdit()
        self.birth_date_to.setPlaceholderText("YYYY-MM-DD")
        self.input_layout.addWidget(QLabel("Born To:"))
        self.input_layout.addWidget(self.birth_date_to)
        
        self.layout.addLayout(self.input_layout)
        
        # --- Search Results Table ---
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(
            ["Name", "Birth Date", "Birth Place", "Death Date", "ID"]
        )
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.layout.addWidget(self.results_table)
        
        # --- Action Buttons ---
        self.action_layout = QHBoxLayout()
        self.view_tree_btn = QPushButton("View in Tree")
        self.view_timeline_btn = QPushButton("View in Timeline")
        
        self.action_layout.addWidget(self.view_tree_btn)
        self.action_layout.addWidget(self.view_timeline_btn)
        self.action_layout.addStretch()
        self.layout.addLayout(self.action_layout)
        
        # --- Debounce Timer for Search ---
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300) # 300ms debounce
        self.search_timer.timeout.connect(self.perform_search)
        
        # --- Signals ---
        self.name_input.textChanged.connect(self.on_search_changed)
        self.birth_place_input.textChanged.connect(self.on_search_changed)
        self.birth_date_from.textChanged.connect(self.on_search_changed)
        self.birth_date_to.textChanged.connect(self.on_search_changed)
        
        self.view_tree_btn.clicked.connect(self.jump_to_tree)
        self.view_timeline_btn.clicked.connect(self.jump_to_timeline)
        
        self.results_table.doubleClicked.connect(self.jump_to_tree)

    def on_search_changed(self):
        self.search_timer.start()
        
    def perform_search(self):
        name_q = self.name_input.text().strip()
        place_q = self.birth_place_input.text().strip()
        date_from = self.birth_date_from.text().strip()
        date_to = self.birth_date_to.text().strip()
        
        if not any([name_q, place_q, date_from, date_to]):
            self.results_table.setRowCount(0)
            return
            
        results = self.person_repo.search(
            name_query=name_q if name_q else None,
            birth_place=place_q if place_q else None,
            birth_date_from=date_from if date_from else None,
            birth_date_to=date_to if date_to else None
        )
        
        display_results = []
        for person in results:
            # If the person was fully redacted (name replaced with Private/Living), 
            # hide them from search unless the query actually matches "private" or "living".
            if getattr(person, '_is_redacted', False) and person.name in ("Private", "Living") and name_q:
                if name_q.lower() not in person.name.lower():
                    continue
            display_results.append(person)
            
        self.results_table.setRowCount(len(display_results))
        for row, person in enumerate(display_results):
            self.results_table.setItem(row, 0, QTableWidgetItem(person.name))
            self.results_table.setItem(row, 1, QTableWidgetItem(person.birth_date_str or ""))
            self.results_table.setItem(row, 2, QTableWidgetItem(person.birth_place or ""))
            self.results_table.setItem(row, 3, QTableWidgetItem(person.death_date_str or ""))
            self.results_table.setItem(row, 4, QTableWidgetItem(person.id))
            
        self.results_table.setColumnHidden(4, True)

    def _selected_person_id(self):
        sel = self.results_table.selectedItems()
        if not sel:
            return None
        return self.results_table.item(sel[0].row(), 4).text()

    def jump_to_tree(self):
        pid = self._selected_person_id()
        if not pid:
            QMessageBox.warning(self, "Selection Required", "Please select a person from the search results.")
            return
            
        # Switch to Tree tab
        self.main_window.tabs.setCurrentWidget(self.main_window.tree_tab)
        
        # Set person as root
        combo = self.main_window.tree_tab.root_person_combo
        index = combo.findData(pid)
        if index >= 0:
            combo.setCurrentIndex(index)

    def jump_to_timeline(self):
        pid = self._selected_person_id()
        if not pid:
            QMessageBox.warning(self, "Selection Required", "Please select a person from the search results.")
            return
            
        # Switch to Timeline tab
        self.main_window.tabs.setCurrentWidget(self.main_window.timeline_tab)
        
        # Set person in timeline filter
        combo = self.main_window.timeline_tab.filter_person_combo
        index = combo.findData(pid)
        if index >= 0:
            combo.setCurrentIndex(index)
