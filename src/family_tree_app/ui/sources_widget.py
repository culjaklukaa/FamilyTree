from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QDialog, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox, QComboBox,
    QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt

from family_tree_app.db import Database
from family_tree_app.models import Source, SourceLink
from family_tree_app.repositories import SourceRepository, SourceLinkRepository


class SourceDialog(QDialog):
    """Dialog to create or edit a Source record."""

    def __init__(self, parent=None, source: Source = None):
        super().__init__(parent)
        self.setWindowTitle("Source / Citation")
        self.source_id = source.id if source else None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.title_input = QLineEdit()
        self.author_input = QLineEdit()
        self.publisher_input = QLineEdit()
        self.pub_date_input = QLineEdit()
        self.url_input = QLineEdit()
        self.notes_input = QTextEdit()

        form.addRow("Title*", self.title_input)
        form.addRow("Author", self.author_input)
        form.addRow("Publisher", self.publisher_input)
        form.addRow("Publication Date", self.pub_date_input)
        form.addRow("URL", self.url_input)
        form.addRow("Notes", self.notes_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if source:
            self._populate(source)

    def _populate(self, s: Source):
        self.title_input.setText(s.title or "")
        self.author_input.setText(s.author or "")
        self.publisher_input.setText(s.publisher or "")
        self.pub_date_input.setText(s.publication_date or "")
        self.url_input.setText(s.url or "")
        self.notes_input.setPlainText(s.notes or "")

    def get_source(self) -> Source:
        kwargs = {
            "title": self.title_input.text(),
            "author": self.author_input.text() or None,
            "publisher": self.publisher_input.text() or None,
            "publication_date": self.pub_date_input.text() or None,
            "url": self.url_input.text() or None,
            "notes": self.notes_input.toPlainText() or None,
        }
        if self.source_id:
            kwargs["id"] = self.source_id
        return Source(**kwargs)

    def accept(self):
        if not self.title_input.text().strip():
            return
        super().accept()


class LinkSourceDialog(QDialog):
    """Dialog to attach an existing source to a fact, with optional detail text."""

    def __init__(self, parent=None, sources: list = None, field_names: list = None):
        super().__init__(parent)
        self.setWindowTitle("Attach Source to Fact")
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.source_combo = QComboBox()
        for s in (sources or []):
            label = s.title
            if s.author:
                label += f" — {s.author}"
            self.source_combo.addItem(label, s.id)

        self.field_combo = QComboBox()
        self.field_combo.addItem("(Entire record)", None)
        for fname in (field_names or []):
            self.field_combo.addItem(fname, fname)

        self.detail_input = QLineEdit()
        self.detail_input.setPlaceholderText("e.g. page 42, entry #3")

        form.addRow("Source", self.source_combo)
        form.addRow("Applies to field", self.field_combo)
        form.addRow("Detail / page", self.detail_input)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        self.new_source_btn = QPushButton("New Source…")
        self.new_source_btn.clicked.connect(self._create_new_source)
        btn_row.addWidget(self.new_source_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._sources = list(sources or [])
        self._source_repo = None  # set externally when needed

    def set_source_repo(self, repo: SourceRepository):
        self._source_repo = repo

    def _create_new_source(self):
        dlg = SourceDialog(self)
        if dlg.exec():
            new_src = dlg.get_source()
            if self._source_repo:
                new_src = self._source_repo.create(new_src)
            self._sources.append(new_src)
            label = new_src.title
            if new_src.author:
                label += f" — {new_src.author}"
            self.source_combo.addItem(label, new_src.id)
            self.source_combo.setCurrentIndex(self.source_combo.count() - 1)

    def get_source_id(self) -> str:
        return self.source_combo.currentData()

    def get_field_name(self):
        return self.field_combo.currentData()

    def get_detail(self) -> str:
        return self.detail_input.text() or None

    def accept(self):
        if self.source_combo.count() == 0:
            return
        super().accept()


# Field names that can be individually cited on a Person record.
PERSON_CITABLE_FIELDS = [
    "name", "maiden_name", "birth_date", "birth_place",
    "death_date", "death_place", "occupation", "notes",
]


class SourcesWidget(QWidget):
    """Reusable widget showing sources linked to a person, event, or relationship."""

    def __init__(self, db: Database, person_id: str = None, event_id: str = None,
                 relationship_id: str = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.source_repo = SourceRepository(db)
        self.link_repo = SourceLinkRepository(db)
        self.person_id = person_id
        self.event_id = event_id
        self.relationship_id = relationship_id

        layout = QVBoxLayout(self)

        btn_row = QHBoxLayout()
        self.attach_btn = QPushButton("Attach Source…")
        self.attach_btn.clicked.connect(self._attach_source)
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self._remove_link)
        btn_row.addWidget(self.attach_btn)
        btn_row.addWidget(self.remove_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Source", "Author", "Field", "Detail", "link_id"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setColumnHidden(4, True)
        layout.addWidget(self.table)

        self._load()

    def _load(self):
        self.table.setRowCount(0)
        if self.person_id:
            links = self.link_repo.get_by_person(self.person_id)
        elif self.event_id:
            links = self.link_repo.get_by_event(self.event_id)
        elif self.relationship_id:
            links = self.link_repo.get_by_relationship(self.relationship_id)
        else:
            return

        self.table.setRowCount(len(links))
        for row, link in enumerate(links):
            source = self.source_repo.get(link.source_id)
            self.table.setItem(row, 0, QTableWidgetItem(source.title if source else "?"))
            self.table.setItem(row, 1, QTableWidgetItem(source.author if source else ""))
            self.table.setItem(row, 2, QTableWidgetItem(link.field_name or "(entire record)"))
            self.table.setItem(row, 3, QTableWidgetItem(link.detail or ""))
            self.table.setItem(row, 4, QTableWidgetItem(link.id))

    def _attach_source(self):
        sources = self.source_repo.get_all()
        fields = PERSON_CITABLE_FIELDS if self.person_id else []

        dlg = LinkSourceDialog(self, sources=sources, field_names=fields)
        dlg.set_source_repo(self.source_repo)
        if dlg.exec():
            link = SourceLink(
                source_id=dlg.get_source_id(),
                person_id=self.person_id,
                event_id=self.event_id,
                relationship_id=self.relationship_id,
                field_name=dlg.get_field_name(),
                detail=dlg.get_detail(),
            )
            self.link_repo.create(link)
            self._load()

    def _remove_link(self):
        sel = self.table.selectedItems()
        if not sel:
            return
        link_id = self.table.item(sel[0].row(), 4).text()
        reply = QMessageBox.question(
            self, "Remove Source",
            "Remove this source citation from the record?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.link_repo.delete(link_id)
            self._load()
