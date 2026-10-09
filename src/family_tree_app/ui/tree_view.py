"""Interactive tree view with igraph Sugiyama layout.

Handles multiple partners and blended families by modelling the family
as a directed graph (parent→child edges) with generation-layer
constraints, then using igraph's Sugiyama layout for crossing
minimisation.  Partnership links are kept on the same layer and drawn
as dashed connectors rather than hierarchical edges.
"""

import networkx as nx
import igraph as ig

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QLabel, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QPen, QBrush, QColor, QFont, QPainter,
    QWheelEvent, QMouseEvent,
)

from family_tree_app.repositories import PersonRepository, RelationshipRepository

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NODE_W = 160
NODE_H = 64
H_GAP = 190          # horizontal spacing multiplier
V_GAP = 130          # vertical spacing multiplier
PARTNER_GAP = 170    # horizontal gap between partners


# ---------------------------------------------------------------------------
# Zoom & Pan view
# ---------------------------------------------------------------------------
class ZoomPanGraphicsView(QGraphicsView):
    """QGraphicsView with mouse-wheel zoom and click-drag pan."""

    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, event: QWheelEvent):
        factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        self.scale(factor, factor)


# ---------------------------------------------------------------------------
# Clickable person node
# ---------------------------------------------------------------------------
class PersonNodeItem(QGraphicsRectItem):
    """Rectangle representing a person.

    Single-click → open detail view.
    Double-click → collapse/expand descendants.
    """

    def __init__(self, person_id, x, y, w, h, tab_ref):
        super().__init__(x, y, w, h)
        self.person_id = person_id
        self.tab_ref = tab_ref
        self.setCursor(Qt.PointingHandCursor)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw subtle drop shadow
        shadow_rect = self.rect().translated(0, 3)
        painter.setBrush(QColor(0, 0, 0, 30))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(shadow_rect, 8, 8)
        
        # Draw main card
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        painter.drawRoundedRect(self.rect(), 8, 8)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.tab_ref.person_clicked.emit(self.person_id)

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        if event.button() == Qt.LeftButton:
            self.tab_ref.toggle_collapse(self.person_id)


# ---------------------------------------------------------------------------
# Layout helper – networkx DiGraph → igraph Sugiyama positions
# ---------------------------------------------------------------------------
def sugiyama_positions(G):
    """Return ``{node_id: (x, y)}`` using igraph's Sugiyama algorithm.

    *G* must be a ``nx.DiGraph`` where every node has a ``generation``
    attribute (int).  Edges should run parent → child (lower gen →
    higher gen).
    """
    if not G.nodes:
        return {}

    nodes = list(G.nodes())
    idx = {n: i for i, n in enumerate(nodes)}

    ig_g = ig.Graph(directed=True)
    ig_g.add_vertices(len(nodes))
    ig_g.add_edges([(idx[u], idx[v]) for u, v in G.edges()])

    gens = [G.nodes[n].get("generation", 0) for n in nodes]
    min_gen = min(gens)
    layers = [g - min_gen for g in gens]

    try:
        layout = ig_g.layout_sugiyama(layers=layers)
        return {
            nodes[i]: (layout.coords[i][0] * H_GAP, layout.coords[i][1] * V_GAP)
            for i in range(len(nodes))
        }
    except Exception:
        # Fallback – should rarely happen
        raw = nx.spring_layout(G)
        return {n: (raw[n][0] * 400, raw[n][1] * 400) for n in raw}


# ---------------------------------------------------------------------------
# Main widget
# ---------------------------------------------------------------------------
class TreeViewTab(QWidget):
    person_clicked = Signal(str)  # emits person_id

    def __init__(self, person_repo: PersonRepository,
                 rel_repo: RelationshipRepository):
        super().__init__()
        self.person_repo = person_repo
        self.rel_repo = rel_repo
        self.collapsed_nodes: set[str] = set()
        self._layout_cache = {}
        self.show_private_data = True

        self._main_layout = QVBoxLayout(self)

        # --- toolbar ---
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Root Person:"))
        self.root_person_combo = QComboBox()
        toolbar.addWidget(self.root_person_combo)
        toolbar.addWidget(QLabel("View Mode:"))
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["Ancestors", "Descendants", "Whole Family"])
        toolbar.addWidget(self.view_mode_combo)
        toolbar.addStretch()
        self._main_layout.addLayout(toolbar)

        # --- scene / view ---
        self.scene = QGraphicsScene()
        self.view = ZoomPanGraphicsView(self.scene)
        self.view.setBackgroundBrush(QBrush(QColor("#ffffff")))
        self.view.setStyleSheet("border: none;")
        self._main_layout.addWidget(self.view)

        # --- signals ---
        self.root_person_combo.currentIndexChanged.connect(self._on_control_changed)
        self.view_mode_combo.currentIndexChanged.connect(self._on_control_changed)

    # ----- public helpers --------------------------------------------------

    def refresh_people_combo(self):
        # Save current selection
        current_id = self.root_person_combo.currentData()
        
        self.clear_cache()
        self.root_person_combo.blockSignals(True)
        self.root_person_combo.clear()
        for p in self.person_repo.get_all():
            self.root_person_combo.addItem(p.name, p.id)
            
        # Restore selection
        if current_id:
            idx = self.root_person_combo.findData(current_id)
            if idx >= 0:
                self.root_person_combo.setCurrentIndex(idx)
                
        self.root_person_combo.blockSignals(False)
        self.draw_tree()

    def toggle_collapse(self, person_id: str):
        self.collapsed_nodes.symmetric_difference_update({person_id})
        self.draw_tree()
        
    def clear_cache(self):
        self._layout_cache.clear()

    # ----- internal --------------------------------------------------------

    def _on_control_changed(self):
        is_whole_family = self.view_mode_combo.currentText() == "Whole Family"
        self.root_person_combo.setEnabled(not is_whole_family)
        self.collapsed_nodes.clear()
        self.draw_tree()

    # =====================================================================
    # Graph building
    # =====================================================================

    @staticmethod
    def _parse_rels(rel_repo):
        rows = rel_repo.db.connection.execute(
            "SELECT * FROM relationships"
        ).fetchall()
        return [
            {"id": r["id"], "a": r["person_a_id"],
             "b": r["person_b_id"], "type": r["type"]}
            for r in rows
        ]

    def _build_ancestors(self, G, root_id, people, rels, partnerships):
        """BFS upward through parent-child links."""
        queue = [(root_id, 0)]
        visited = {root_id}
        while queue:
            cur, gen = queue.pop(0)
            if cur in people:
                G.add_node(cur, generation=-gen)
            if cur in self.collapsed_nodes:
                continue
            for r in rels:
                if r["b"] == cur and r["type"].startswith("parent-child"):
                    pid = r["a"]
                    G.add_edge(pid, cur, rel_type=r["type"])
                    if pid not in visited:
                        visited.add(pid)
                        queue.append((pid, gen + 1))
        # Collect partnership edges among nodes already in the graph
        for r in rels:
            if r["type"].startswith("partnership"):
                if r["a"] in G.nodes and r["b"] in G.nodes:
                    partnerships.append((r["a"], r["b"], r["type"]))

    def _build_descendants(self, G, root_id, people, rels, partnerships):
        """BFS downward through parent-child links."""
        queue = [(root_id, 0)]
        visited = {root_id}
        while queue:
            cur, gen = queue.pop(0)
            if cur in people:
                G.add_node(cur, generation=gen)
            if cur in self.collapsed_nodes:
                continue
            for r in rels:
                if r["a"] == cur and r["type"].startswith("parent-child"):
                    cid = r["b"]
                    G.add_edge(cur, cid, rel_type=r["type"])
                    if cid not in visited:
                        visited.add(cid)
                        queue.append((cid, gen + 1))
        for r in rels:
            if r["type"].startswith("partnership"):
                if r["a"] in G.nodes and r["b"] in G.nodes:
                    partnerships.append((r["a"], r["b"], r["type"]))

    def _build_whole_family(self, G, people, rels, partnerships):
        """BFS in all directions, assigning generation layers."""
        # Find connected components via undirected graph
        UG = nx.Graph()
        for pid in people:
            UG.add_node(pid)
        for r in rels:
            UG.add_edge(r["a"], r["b"])
            
        components = list(nx.connected_components(UG))
        visited = {}

        for comp in components:
            if not comp:
                continue
            
            comp_root = list(comp)[0]
            queue = [(comp_root, 0)]
            visited[comp_root] = 0

            while queue:
                cur, gen = queue.pop(0)
                if cur in self.collapsed_nodes:
                    continue
                for r in rels:
                    # Forward: cur is person_a
                    if r["a"] == cur and r["b"] in comp:
                        other = r["b"]
                        if r["type"].startswith("parent-child"):
                            new_gen = gen + 1
                            G.add_edge(cur, other, rel_type=r["type"])
                        elif r["type"].startswith("partnership"):
                            new_gen = gen
                            partnerships.append((cur, other, r["type"]))
                        else:
                            continue
                        if other not in visited:
                            visited[other] = new_gen
                            queue.append((other, new_gen))
                    # Reverse: cur is person_b
                    elif r["b"] == cur and r["a"] in comp:
                        other = r["a"]
                        if r["type"].startswith("parent-child"):
                            new_gen = gen - 1
                            G.add_edge(other, cur, rel_type=r["type"])
                        elif r["type"].startswith("partnership"):
                            new_gen = gen
                            partnerships.append((other, cur, r["type"]))
                        else:
                            continue
                        if other not in visited:
                            visited[other] = new_gen
                            queue.append((other, new_gen))

        for node, gen in visited.items():
            if node in people:
                G.add_node(node, generation=gen)

    # =====================================================================
    # Drawing
    # =====================================================================

    def draw_tree(self):
        self.scene.clear()

        if self.root_person_combo.count() == 0:
            return
            
        mode = self.view_mode_combo.currentText()
        root_id = self.root_person_combo.currentData()
        if not root_id and mode != "Whole Family":
            return

        people = {p.id: p for p in self.person_repo.get_all()}
        
        # Don't cache by root_id for Whole Family since it ignores root_id
        cache_key = (root_id if mode != "Whole Family" else None, mode, frozenset(self.collapsed_nodes))
        if cache_key in self._layout_cache:
            G, partnerships, pos = self._layout_cache[cache_key]
        else:
            rels = self._parse_rels(self.rel_repo)
            G = nx.DiGraph()
            partnerships: list[tuple[str, str, str]] = []

            if mode == "Ancestors":
                self._build_ancestors(G, root_id, people, rels, partnerships)
            elif mode == "Descendants":
                self._build_descendants(G, root_id, people, rels, partnerships)
            else:
                self._build_whole_family(G, people, rels, partnerships)

            if not G.nodes:
                return

            pos = sugiyama_positions(G)
            if not pos:
                return
                
            self._layout_cache[cache_key] = (G, partnerships, pos)

        # --- draw partnership connectors (dashed) -------------------------
        seen_pairs: set[tuple[str, str]] = set()
        for a, b, r_type in partnerships:
            if a not in pos or b not in pos:
                continue
            pair = (min(a, b), max(a, b))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            
            # Default partnership pen
            color = QColor("#E67E22")  # Orange-ish
            style = Qt.DashLine
            if r_type == "partnership:divorced":
                color = QColor("#E74C3C")  # Red
                style = Qt.DotLine
            elif r_type == "partnership:widowed":
                color = QColor("#34495E")  # Dark grey
                style = Qt.DashLine
            elif r_type == "partnership:partner":
                color = QColor("#9B59B6")  # Purple
                style = Qt.DashDotLine
                
            partner_pen = QPen(color, 2, style)
            
            ax, ay = pos[a]
            bx, by = pos[b]
            self.scene.addLine(
                ax + NODE_W / 2, ay + NODE_H / 2,
                bx + NODE_W / 2, by + NODE_H / 2,
                partner_pen,
            )

        # --- draw parent→child edges (solid) ------------------------------
        for u, v, data in G.edges(data=True):
            r_type = data.get("rel_type", "")
            
            color = QColor("#7F8C8D")  # Grey
            style = Qt.SolidLine
            if r_type == "parent-child:adopted":
                color = QColor("#2980B9")  # Blue
                style = Qt.DashLine
            elif r_type == "parent-child:step":
                color = QColor("#16A085")  # Green
                style = Qt.DotLine
            elif r_type == "parent-child:foster":
                color = QColor("#8E44AD")  # Purple
                style = Qt.DashDotLine
                
            edge_pen = QPen(color, 2, style)
            
            ux, uy = pos[u]
            vx, vy = pos[v]
            self.scene.addLine(
                ux + NODE_W / 2, uy + NODE_H,
                vx + NODE_W / 2, vy,
                edge_pen,
            )

        # --- draw nodes ---------------------------------------------------
        from family_tree_app.privacy import apply_privacy, get_privacy_settings
        normal_brush = QBrush(QColor("#2c3e50"))      # Dark blue/grey
        collapsed_brush = QBrush(QColor("#1a252f"))   # Darker for collapsed
        unverified_brush = QBrush(QColor("#d35400"))  # Dark orange
        private_brush = QBrush(QColor("#8e44ad"))     # Dark purple
        node_pen = QPen(QColor("#1a252f"), 2)
        unverified_pen = QPen(QColor("#e67e22"), 2, Qt.DashLine)
        private_pen = QPen(QColor("#9b59b6"), 2, Qt.DashDotLine)
        font = QFont("Segoe UI", 10, QFont.Bold)

        for node in G.nodes():
            x, y = pos[node]
            is_collapsed = node in self.collapsed_nodes
            person = people.get(node)
            is_unverified = person.unverified if person else False
            has_privacy = bool(get_privacy_settings(person)) if person else False

            rect = PersonNodeItem(node, x, y, NODE_W, NODE_H, self)
            if has_privacy and getattr(person, '_is_redacted', False):
                rect.setPen(private_pen)
            elif is_unverified:
                rect.setPen(unverified_pen)
            else:
                rect.setPen(node_pen)

            if is_collapsed:
                rect.setBrush(collapsed_brush)
            elif has_privacy and getattr(person, '_is_redacted', False):
                rect.setBrush(private_brush)
            elif is_unverified:
                rect.setBrush(unverified_brush)
            else:
                rect.setBrush(normal_brush)
            self.scene.addItem(rect)

            name = person.name if person else "?"
            if len(name) > 16:
                name = name[:14] + "…"
            if is_collapsed:
                name += " ▶"
            if is_unverified:
                name += " ⚠"
            if has_privacy:
                name += " 🔒"

            text_name = self.scene.addText(name, font)
            text_name.setDefaultTextColor(QColor("#ffffff"))
            text_name.setParentItem(rect)
            text_name.setAcceptedMouseButtons(Qt.NoButton)
            
            dates_str = ""
            if person and not (has_privacy and getattr(person, '_is_redacted', False)):
                b_date = person.birth_date_str or person.birth_date or ""
                d_date = person.death_date_str or person.death_date or ""
                if b_date or d_date:
                    import re
                    def get_year(d):
                        if not d: return ""
                        m = re.search(r'\d{4}', d)
                        return m.group(0) if m else d[:4]
                    
                    b_year = get_year(b_date)
                    d_year = get_year(d_date)
                    
                    if b_year or d_year:
                        b_year = b_year or "?"
                        if d_year:
                            dates_str = f"{b_year} - {d_year}"
                        else:
                            dates_str = f"{b_year}"

            if dates_str:
                small_font = QFont("Segoe UI", 9)
                text_dates = self.scene.addText(dates_str, small_font)
                text_dates.setDefaultTextColor(QColor("#ecf0f1"))
                text_dates.setParentItem(rect)
                text_dates.setAcceptedMouseButtons(Qt.NoButton)
                
                tn_b = text_name.boundingRect()
                td_b = text_dates.boundingRect()
                total_h = tn_b.height() + td_b.height() - 8
                
                start_y = y + (NODE_H - total_h) / 2
                text_name.setPos(x + (NODE_W - tn_b.width()) / 2, start_y)
                text_dates.setPos(x + (NODE_W - td_b.width()) / 2, start_y + tn_b.height() - 6)
            else:
                tb = text_name.boundingRect()
                text_name.setPos(
                    x + (NODE_W - tb.width()) / 2,
                    y + (NODE_H - tb.height()) / 2,
                )

        self.scene.setSceneRect(
            self.scene.itemsBoundingRect().adjusted(-60, -60, 60, 60)
        )
