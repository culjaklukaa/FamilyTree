"""Tests for sibling derivation — run in isolation, no DB required.

Families tested
---------------
1. Two full siblings (share both parents)
2. Half-siblings (share exactly one parent)
3. Step-siblings (parents partnered, no shared bio parent)
4. Mixed family: full + half + step in one graph
5. Single known parent (only one parent recorded)
6. Three marriages (one parent has children with three partners)
7. No parent-child links → no siblings
8. Adopted child counts as full sibling with bio children of same parents
9. Step-parent's bio child is step-sibling, not half-sibling
10. Person with no siblings at all
"""

import pytest
from family_tree_app.models import Relationship
from family_tree_app.siblings import derive_siblings, get_siblings_for, SiblingLink


# ── helpers ──────────────────────────────────────────────────────────
def _rel(parent, child, rtype="parent-child:biological"):
    return Relationship(person_a_id=parent, person_b_id=child, type=rtype, id=f"{parent}->{child}")


def _partner(a, b, ptype="partnership:married"):
    return Relationship(person_a_id=a, person_b_id=b, type=ptype, id=f"{a}<>{b}")


def _links_by_pair(links):
    """Return {frozenset(a,b): kind} for easy assertion."""
    return {frozenset({l.person_a_id, l.person_b_id}): l.kind for l in links}


# ── 1. Two full siblings ────────────────────────────────────────────
def test_full_siblings():
    """
    Dad ═══ Mom
     │       │
     ├── Alice
     └── Bob
    """
    rels = [
        _rel("dad", "alice"),
        _rel("mom", "alice"),
        _rel("dad", "bob"),
        _rel("mom", "bob"),
    ]
    links = derive_siblings(rels)
    assert len(links) == 1
    assert links[0].kind == "full-sibling"
    assert links[0].pair == frozenset({"alice", "bob"})


# ── 2. Half-siblings ────────────────────────────────────────────────
def test_half_siblings():
    """
    Dad ═══ Mom1        Dad ═══ Mom2
         │                   │
       Alice                Bob
    """
    rels = [
        _rel("dad", "alice"),
        _rel("mom1", "alice"),
        _rel("dad", "bob"),
        _rel("mom2", "bob"),
    ]
    links = derive_siblings(rels)
    assert len(links) == 1
    assert links[0].kind == "half-sibling"


# ── 3. Step-siblings ────────────────────────────────────────────────
def test_step_siblings():
    """
    Dad ════════ StepMom
     │              │
    Alice          Bob
    (bio child)  (bio child of StepMom from prev. relationship)
    """
    rels = [
        _rel("dad", "alice"),
        _rel("stepmom", "bob"),
        _partner("dad", "stepmom"),
        # Bob has a step-parent link to Dad
        _rel("dad", "bob", "parent-child:step"),
    ]
    links = derive_siblings(rels)
    by_pair = _links_by_pair(links)
    assert by_pair[frozenset({"alice", "bob"})] == "step-sibling"


# ── 4. Mixed family ─────────────────────────────────────────────────
def test_mixed_family():
    """
    Mom1 ═ Dad ═ Mom2
      │     │      │
    Alice  Bob   Carol   (Bob is Dad+Mom1's bio child too)
           │
      also Dad+Mom2 bio child? No — let's make Bob only Mom1's child.

    Clarified:
      Dad + Mom1 → Alice, Bob   (full siblings)
      Dad + Mom2 → Carol        (half-sibling to Alice & Bob)
      Mom2 had a previous child Dan (step-sibling to Alice & Bob via Dad-Mom2 partnership)
    """
    rels = [
        # Dad + Mom1 → Alice, Bob
        _rel("dad", "alice"),
        _rel("mom1", "alice"),
        _rel("dad", "bob"),
        _rel("mom1", "bob"),
        # Dad + Mom2 → Carol
        _rel("dad", "carol"),
        _rel("mom2", "carol"),
        # Dad ═ Mom2 partnership
        _partner("dad", "mom2"),
        # Mom2's previous child Dan (bio parent: Mom2 + OtherDad)
        _rel("mom2", "dan"),
        _rel("otherdad", "dan"),
        # Dan has Dad as step-parent
        _rel("dad", "dan", "parent-child:step"),
    ]
    by_pair = _links_by_pair(derive_siblings(rels))

    # Alice & Bob: full siblings (share Dad + Mom1)
    assert by_pair[frozenset({"alice", "bob"})] == "full-sibling"

    # Alice & Carol: half-siblings (share Dad only)
    assert by_pair[frozenset({"alice", "carol"})] == "half-sibling"
    # Bob & Carol: half-siblings (share Dad only)
    assert by_pair[frozenset({"bob", "carol"})] == "half-sibling"

    # Carol & Dan: half-siblings (share Mom2)
    assert by_pair[frozenset({"carol", "dan"})] == "half-sibling"

    # Alice & Dan: step-siblings (Dad partners Mom2, Dan's parent)
    assert by_pair[frozenset({"alice", "dan"})] == "step-sibling"
    # Bob & Dan: step-siblings (same reasoning)
    assert by_pair[frozenset({"bob", "dan"})] == "step-sibling"


# ── 5. Single known parent ──────────────────────────────────────────
def test_single_known_parent():
    """Only one parent is recorded for both children → half-sibling."""
    rels = [
        _rel("dad", "alice"),
        _rel("dad", "bob"),
    ]
    links = derive_siblings(rels)
    assert len(links) == 1
    assert links[0].kind == "half-sibling"


# ── 6. Three marriages ──────────────────────────────────────────────
def test_three_marriages():
    """
    Dad has children with three different partners.
    Child1 (Dad+W1), Child2 (Dad+W2), Child3 (Dad+W3)
    All are half-siblings to each other.
    """
    rels = [
        _rel("dad", "c1"), _rel("w1", "c1"),
        _rel("dad", "c2"), _rel("w2", "c2"),
        _rel("dad", "c3"), _rel("w3", "c3"),
    ]
    links = derive_siblings(rels)
    by_pair = _links_by_pair(links)
    assert len(by_pair) == 3
    assert by_pair[frozenset({"c1", "c2"})] == "half-sibling"
    assert by_pair[frozenset({"c1", "c3"})] == "half-sibling"
    assert by_pair[frozenset({"c2", "c3"})] == "half-sibling"


# ── 7. No parent-child links ────────────────────────────────────────
def test_no_parent_links():
    """Only partnerships, no parent-child → no siblings."""
    rels = [
        _partner("a", "b"),
        _partner("c", "d"),
    ]
    assert derive_siblings(rels) == []


# ── 8. Adopted child counts as full sibling ─────────────────────────
def test_adopted_counts_as_full():
    """An adopted child of the same two parents is a full sibling."""
    rels = [
        _rel("dad", "bio_child"),
        _rel("mom", "bio_child"),
        _rel("dad", "adopted_child", "parent-child:adopted"),
        _rel("mom", "adopted_child", "parent-child:adopted"),
    ]
    links = derive_siblings(rels)
    assert len(links) == 1
    assert links[0].kind == "full-sibling"


# ── 9. Step-parent's bio child is step-sibling ──────────────────────
def test_step_parent_bio_child():
    """
    Mom ═══ StepDad
     │          │
    Alice      Bob  (Bob is StepDad's bio child from prior relationship)
    StepDad is Alice's step-parent.
    """
    rels = [
        _rel("mom", "alice"),
        _rel("stepdad", "alice", "parent-child:step"),
        _rel("stepdad", "bob"),
        _rel("othermom", "bob"),
        _partner("mom", "stepdad"),
    ]
    links = derive_siblings(rels)
    assert len(links) == 1
    assert links[0].kind == "step-sibling"


# ── 10. Person with no siblings ─────────────────────────────────────
def test_only_child():
    """A person with parents but no siblings returns empty."""
    rels = [
        _rel("dad", "alice"),
        _rel("mom", "alice"),
    ]
    assert get_siblings_for("alice", rels) == []


# ── 11. get_siblings_for filters correctly ───────────────────────────
def test_get_siblings_for_filters():
    rels = [
        _rel("dad", "alice"),
        _rel("mom", "alice"),
        _rel("dad", "bob"),
        _rel("mom", "bob"),
        _rel("dad", "carol"),
        _rel("mom2", "carol"),
    ]
    alice_sibs = get_siblings_for("alice", rels)
    assert len(alice_sibs) == 2  # bob (full), carol (half)

    carol_sibs = get_siblings_for("carol", rels)
    assert len(carol_sibs) == 2  # alice (half), bob (half)

    # non-existent person
    assert get_siblings_for("nobody", rels) == []
