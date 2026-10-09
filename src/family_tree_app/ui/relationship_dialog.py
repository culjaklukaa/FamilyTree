from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QLineEdit,
    QDialogButtonBox, QCheckBox, QLabel
)
from family_tree_app.models import Person, Relationship
from typing import List

# Relationship type constants
PARENT_CHILD_TYPES = [
    ("parent-child:biological", "Parent–Child (Biological)"),
    ("parent-child:adopted", "Parent–Child (Adopted)"),
    ("parent-child:step", "Parent–Child (Step)"),
    ("parent-child:foster", "Parent–Child (Foster)"),
]

PARTNERSHIP_TYPES = [
    ("partnership:married", "Partnership (Married)"),
    ("partnership:divorced", "Partnership (Divorced)"),
    ("partnership:widowed", "Partnership (Widowed)"),
    ("partnership:partner", "Partnership (Unmarried Partner)"),
]

SIBLING_TYPES = [
    ("sibling:biological", "Sibling (Biological)"),
    ("sibling:half", "Sibling (Half)"),
    ("sibling:step", "Sibling (Step)"),
    ("sibling:adopted", "Sibling (Adopted)"),
]

EXTENDED_FAMILY_TYPES = [
    ("extended:grandparent-grandchild", "Grandparent – Grandchild"),
    ("extended:great-grandparent", "Great-Grandparent – Great-Grandchild"),
    ("extended:aunt-uncle-niece-nephew", "Aunt/Uncle – Niece/Nephew"),
    ("extended:great-aunt-uncle", "Great-Aunt/Uncle – Great-Niece/Nephew"),
    ("extended:cousin", "Cousin"),
    ("extended:second-cousin", "Second Cousin"),
    ("extended:in-law", "In-Law"),
]

ALL_RELATIONSHIP_TYPES = PARENT_CHILD_TYPES + PARTNERSHIP_TYPES + SIBLING_TYPES + EXTENDED_FAMILY_TYPES


class RelationshipDialog(QDialog):
    """Dialog for adding or editing a relationship between two people."""

    def __init__(self, parent=None, persons: List[Person] = None,
                 relationship: Relationship = None):
        super().__init__(parent)
        self.setWindowTitle("Relationship Details")
        self.setMinimumWidth(400)
        self.relationship_id = relationship.id if relationship else None
        self.persons = persons or []

        self._layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        # --- Person A selector ---
        self.person_a_combo = QComboBox()
        for p in self.persons:
            self.person_a_combo.addItem(p.name, p.id)

        # --- Person B selector ---
        self.person_b_combo = QComboBox()
        for p in self.persons:
            self.person_b_combo.addItem(p.name, p.id)

        # --- Relationship type ---
        self.type_combo = QComboBox()
        for type_key, type_label in ALL_RELATIONSHIP_TYPES:
            self.type_combo.addItem(type_label, type_key)

        # --- Date fields ---
        self.start_date_str_input = QLineEdit()
        self.start_date_str_input.setPlaceholderText("e.g. circa 1945, June 1960")
        self.start_date_input = QLineEdit()
        self.start_date_input.setPlaceholderText("YYYY-MM-DD")
        self.end_date_str_input = QLineEdit()
        self.end_date_str_input.setPlaceholderText("e.g. circa 1970")
        self.end_date_input = QLineEdit()
        self.end_date_input.setPlaceholderText("YYYY-MM-DD")

        self.unverified_checkbox = QCheckBox("Unverified")

        # --- Layout ---
        self.form_layout.addRow("Person A*", self.person_a_combo)
        self.form_layout.addRow("Person B*", self.person_b_combo)
        self.form_layout.addRow("Type*", self.type_combo)
        self.form_layout.addRow("Start Date (Display)", self.start_date_str_input)
        self.form_layout.addRow("Start Date (YYYY-MM-DD)", self.start_date_input)
        self.form_layout.addRow("End Date (Display)", self.end_date_str_input)
        self.form_layout.addRow("End Date (YYYY-MM-DD)", self.end_date_input)
        self.form_layout.addRow("", self.unverified_checkbox)

        self._layout.addLayout(self.form_layout)

        # --- Hint label for parent-child ---
        self.hint_label = QLabel(
            "<i>For parent/grandparent/aunt/uncle relationships:<br>Person A is the older generation (Parent, Grandparent, Aunt/Uncle),<br>Person B is the younger generation (Child, Grandchild, Niece/Nephew).</i>"
        )
        self._layout.addWidget(self.hint_label)

        # --- Buttons ---
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self._layout.addWidget(self.button_box)

        if relationship:
            self._populate_fields(relationship)

    # ------------------------------------------------------------------
    def _populate_fields(self, rel: Relationship):
        idx_a = self.person_a_combo.findData(rel.person_a_id)
        if idx_a >= 0:
            self.person_a_combo.setCurrentIndex(idx_a)
        idx_b = self.person_b_combo.findData(rel.person_b_id)
        if idx_b >= 0:
            self.person_b_combo.setCurrentIndex(idx_b)

        idx_type = self.type_combo.findData(rel.type)
        if idx_type >= 0:
            self.type_combo.setCurrentIndex(idx_type)

        self.start_date_str_input.setText(rel.start_date_str or "")
        self.start_date_input.setText(rel.start_date or "")
        self.end_date_str_input.setText(rel.end_date_str or "")
        self.end_date_input.setText(rel.end_date or "")
        self.unverified_checkbox.setChecked(rel.unverified)

    # ------------------------------------------------------------------
    def get_relationship(self) -> Relationship:
        kwargs = {
            "person_a_id": self.person_a_combo.currentData(),
            "person_b_id": self.person_b_combo.currentData(),
            "type": self.type_combo.currentData(),
            "start_date_str": self.start_date_str_input.text() or None,
            "start_date": self.start_date_input.text() or None,
            "end_date_str": self.end_date_str_input.text() or None,
            "end_date": self.end_date_input.text() or None,
            "unverified": self.unverified_checkbox.isChecked(),
        }
        if self.relationship_id:
            kwargs["id"] = self.relationship_id
        return Relationship(**kwargs)

    # ------------------------------------------------------------------
    def accept(self):
        person_a = self.person_a_combo.currentData()
        person_b = self.person_b_combo.currentData()
        if not person_a or not person_b:
            return
        if person_a == person_b:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "Invalid",
                "Person A and Person B must be different people."
            )
            return
        super().accept()
