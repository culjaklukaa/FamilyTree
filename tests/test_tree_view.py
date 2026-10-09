"""Unit tests for tree_view graph-building and Sugiyama layout.

Tests the three graph-building steps (ancestors, descendants, whole-family)
against small hand-built families, including multiple partners and blended
families.
"""

import networkx as nx
import pytest

from family_tree_app.ui.tree_view import sugiyama_positions


# ---------------------------------------------------------------------------
# Helpers – a lightweight stub that mimics TreeViewTab's graph builders
#           without needing Qt or a database.
# ---------------------------------------------------------------------------

def _rels_from_tuples(tuples):
    """Convert [(a, b, type), ...] → list of dicts."""
    return [{"id": str(i), "a": a, "b": b, "type": t}
            for i, (a, b, t) in enumerate(tuples)]


class _FakeTab:
    """Minimal stand-in for TreeViewTab so we can call build methods."""
    def __init__(self, collapsed=None):
        self.collapsed_nodes = collapsed or set()


def _build_ancestors(root_id, people, rels, collapsed=None):
    from family_tree_app.ui.tree_view import TreeViewTab
    tab = _FakeTab(collapsed)
    G = nx.DiGraph()
    partnerships = []
    TreeViewTab._build_ancestors(tab, G, root_id, people, rels, partnerships)
    return G, partnerships


def _build_descendants(root_id, people, rels, collapsed=None):
    from family_tree_app.ui.tree_view import TreeViewTab
    tab = _FakeTab(collapsed)
    G = nx.DiGraph()
    partnerships = []
    TreeViewTab._build_descendants(tab, G, root_id, people, rels, partnerships)
    return G, partnerships


def _build_whole_family(root_id, people, rels, collapsed=None):
    from family_tree_app.ui.tree_view import TreeViewTab
    tab = _FakeTab(collapsed)
    G = nx.DiGraph()
    partnerships = []
    TreeViewTab._build_whole_family(tab, G, people, rels, partnerships)
    return G, partnerships


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAncestorsGraph:
    """Ancestors mode: BFS upward from the root."""

    def test_single_person(self):
        people = {"A": None}
        rels = []
        G, parts = _build_ancestors("A", people, _rels_from_tuples(rels))
        assert set(G.nodes) == {"A"}
        assert list(G.edges) == []
        assert parts == []

    def test_two_parents(self):
        people = {"child": None, "mom": None, "dad": None}
        rels = [
            ("mom", "child", "parent-child:biological"),
            ("dad", "child", "parent-child:biological"),
        ]
        G, _ = _build_ancestors("child", people, _rels_from_tuples(rels))
        assert set(G.nodes) == {"child", "mom", "dad"}
        assert ("mom", "child") in G.edges
        assert ("dad", "child") in G.edges
        # child at generation 0, parents at generation -1
        assert G.nodes["child"]["generation"] == 0
        assert G.nodes["mom"]["generation"] == -1
        assert G.nodes["dad"]["generation"] == -1

    def test_grandparents(self):
        people = {"C": None, "P": None, "GP": None}
        rels = [("P", "C", "parent-child:biological"),
                ("GP", "P", "parent-child:biological")]
        G, _ = _build_ancestors("C", people, _rels_from_tuples(rels))
        assert G.nodes["C"]["generation"] == 0
        assert G.nodes["P"]["generation"] == -1
        assert G.nodes["GP"]["generation"] == -2

    def test_collapsed_stops_traversal(self):
        people = {"C": None, "P": None, "GP": None}
        rels = [("P", "C", "parent-child:biological"),
                ("GP", "P", "parent-child:biological")]
        G, _ = _build_ancestors("C", people, _rels_from_tuples(rels),
                                collapsed={"P"})
        assert "P" in G.nodes
        assert "GP" not in G.nodes  # traversal stopped at P

    def test_partnership_collected(self):
        people = {"C": None, "mom": None, "dad": None}
        rels = [
            ("mom", "C", "parent-child:biological"),
            ("dad", "C", "parent-child:biological"),
            ("mom", "dad", "partnership:married"),
        ]
        G, parts = _build_ancestors("C", people, _rels_from_tuples(rels))
        pair_set = {(min(a, b), max(a, b)) for a, b, _ in parts}
        assert ("dad", "mom") in pair_set or ("mom", "dad") in pair_set


class TestDescendantsGraph:

    def test_two_children(self):
        people = {"P": None, "C1": None, "C2": None}
        rels = [("P", "C1", "parent-child:biological"),
                ("P", "C2", "parent-child:biological")]
        G, _ = _build_descendants("P", people, _rels_from_tuples(rels))
        assert set(G.nodes) == {"P", "C1", "C2"}
        assert G.nodes["P"]["generation"] == 0
        assert G.nodes["C1"]["generation"] == 1
        assert G.nodes["C2"]["generation"] == 1


class TestWholeFamily:

    def test_blended_family(self):
        """Two partners who each have children from prior relationships.

        mom -- dad1  (married, children: C1)
        mom -- dad2  (married, children: C2)
        C1 and C2 are half-siblings via mom.
        """
        people = {"mom": None, "dad1": None, "dad2": None,
                  "C1": None, "C2": None}
        rels = [
            ("mom", "C1", "parent-child:biological"),
            ("dad1", "C1", "parent-child:biological"),
            ("mom", "C2", "parent-child:biological"),
            ("dad2", "C2", "parent-child:biological"),
            ("mom", "dad1", "partnership:divorced"),
            ("mom", "dad2", "partnership:married"),
        ]
        G, parts = _build_whole_family("mom", people, _rels_from_tuples(rels))
        assert set(G.nodes) == {"mom", "dad1", "dad2", "C1", "C2"}
        # mom, dad1, dad2 should all be at the same generation
        assert G.nodes["mom"]["generation"] == G.nodes["dad1"]["generation"]
        assert G.nodes["mom"]["generation"] == G.nodes["dad2"]["generation"]
        # children one generation below
        parent_gen = G.nodes["mom"]["generation"]
        assert G.nodes["C1"]["generation"] == parent_gen + 1
        assert G.nodes["C2"]["generation"] == parent_gen + 1
        # partnerships recorded
        pair_set = {(min(a, b), max(a, b)) for a, b, _ in parts}
        assert ("dad1", "mom") in pair_set or ("mom", "dad1") in pair_set

    def test_three_marriages(self):
        """One person married three times, each with a child."""
        people = {"P": None, "S1": None, "S2": None, "S3": None,
                  "C1": None, "C2": None, "C3": None}
        rels = [
            ("P", "S1", "partnership:divorced"),
            ("P", "S2", "partnership:divorced"),
            ("P", "S3", "partnership:married"),
            ("P", "C1", "parent-child:biological"),
            ("S1", "C1", "parent-child:biological"),
            ("P", "C2", "parent-child:biological"),
            ("S2", "C2", "parent-child:biological"),
            ("P", "C3", "parent-child:biological"),
            ("S3", "C3", "parent-child:biological"),
        ]
        G, parts = _build_whole_family("P", people, _rels_from_tuples(rels))
        assert len(G.nodes) == 7
        parent_gen = G.nodes["P"]["generation"]
        for s in ("S1", "S2", "S3"):
            assert G.nodes[s]["generation"] == parent_gen
        for c in ("C1", "C2", "C3"):
            assert G.nodes[c]["generation"] == parent_gen + 1


class TestSugiyamaPositions:

    def test_empty_graph(self):
        G = nx.DiGraph()
        assert sugiyama_positions(G) == {}

    def test_single_node(self):
        G = nx.DiGraph()
        G.add_node("A", generation=0)
        pos = sugiyama_positions(G)
        assert "A" in pos

    def test_parent_child_ordering(self):
        """Parent should be above (lower y) than child."""
        G = nx.DiGraph()
        G.add_node("P", generation=0)
        G.add_node("C", generation=1)
        G.add_edge("P", "C")
        pos = sugiyama_positions(G)
        assert pos["P"][1] < pos["C"][1]

    def test_siblings_same_y(self):
        """Two children of the same parent should share the same y."""
        G = nx.DiGraph()
        G.add_node("P", generation=0)
        G.add_node("C1", generation=1)
        G.add_node("C2", generation=1)
        G.add_edge("P", "C1")
        G.add_edge("P", "C2")
        pos = sugiyama_positions(G)
        assert pos["C1"][1] == pos["C2"][1]

    def test_blended_layout(self):
        """Multiple parents, shared child – no crash, correct layers."""
        G = nx.DiGraph()
        G.add_node("mom", generation=0)
        G.add_node("dad", generation=0)
        G.add_node("child", generation=1)
        G.add_edge("mom", "child")
        G.add_edge("dad", "child")
        pos = sugiyama_positions(G)
        assert len(pos) == 3
        assert pos["mom"][1] == pos["dad"][1]
        assert pos["child"][1] > pos["mom"][1]
