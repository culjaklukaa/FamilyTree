"""Pure functions for deriving sibling relationships from parent links.

Sibling relationships are *computed*, never stored in the DB.  The logic
only needs a list of Relationship objects — no database access required —
which makes it easy to unit-test against hand-built families.

Definitions used here
---------------------
* **Full siblings** – share two or more biological/adopted parents.
* **Half-siblings** – share exactly one biological/adopted parent.
* **Step-siblings** – share zero biological/adopted parents, but at
  least one parent of each child is in a partnership with a parent of
  the other child (i.e. they are connected through a step-parent).

Convention: in every parent-child relationship, Person A is the parent
and Person B is the child.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Set, Tuple

from .models import Relationship

# Parent-child subtypes that count for biological/adopted parentage
_BIO_ADOPTED_TYPES = frozenset({
    "parent-child:biological",
    "parent-child:adopted",
})

# All parent-child subtypes (including step / foster)
_ALL_PARENT_CHILD_TYPES = frozenset({
    "parent-child:biological",
    "parent-child:adopted",
    "parent-child:step",
    "parent-child:foster",
})

# All partnership subtypes
_PARTNERSHIP_TYPES = frozenset({
    "partnership:married",
    "partnership:divorced",
    "partnership:widowed",
    "partnership:partner",
})


@dataclass(frozen=True)
class SiblingLink:
    """A derived sibling relationship between two people."""
    person_a_id: str
    person_b_id: str
    kind: str  # "full-sibling", "half-sibling", or "step-sibling"

    @property
    def pair(self) -> FrozenSet[str]:
        return frozenset({self.person_a_id, self.person_b_id})


def derive_siblings(relationships: List[Relationship]) -> List[SiblingLink]:
    """Derive all sibling links from a flat list of relationships.

    Returns a deduplicated list of ``SiblingLink`` objects.  The same
    pair of people will appear at most once, with the *strongest* link
    winning: full > half > step.
    """
    # 1. Build child → set-of-bio/adopted-parents
    bio_parents: Dict[str, Set[str]] = defaultdict(set)
    # 2. Build child → set-of-ALL-parents (including step/foster)
    all_parents: Dict[str, Set[str]] = defaultdict(set)
    # 3. Build partner pairs (undirected)
    partner_pairs: Set[FrozenSet[str]] = set()

    for rel in relationships:
        if rel.type in _ALL_PARENT_CHILD_TYPES:
            parent_id, child_id = rel.person_a_id, rel.person_b_id
            all_parents[child_id].add(parent_id)
            if rel.type in _BIO_ADOPTED_TYPES:
                bio_parents[child_id].add(parent_id)
        elif rel.type in _PARTNERSHIP_TYPES:
            partner_pairs.add(frozenset({rel.person_a_id, rel.person_b_id}))

    # Collect all children (anyone who appears as Person B in a parent-child rel)
    all_children = list(all_parents.keys())

    # 4. Compare every pair of children
    best: Dict[FrozenSet[str], SiblingLink] = {}
    _PRIORITY = {"full-sibling": 0, "half-sibling": 1, "step-sibling": 2}

    for i in range(len(all_children)):
        for j in range(i + 1, len(all_children)):
            child_x = all_children[i]
            child_y = all_children[j]
            pair = frozenset({child_x, child_y})

            shared_bio = bio_parents[child_x] & bio_parents[child_y]

            if len(shared_bio) >= 2:
                kind = "full-sibling"
            elif len(shared_bio) == 1:
                kind = "half-sibling"
            else:
                # Check for step-sibling: a parent of X partners with a parent of Y
                is_step = False
                for px in all_parents[child_x]:
                    for py in all_parents[child_y]:
                        if frozenset({px, py}) in partner_pairs:
                            is_step = True
                            break
                    if is_step:
                        break
                if not is_step:
                    continue
                kind = "step-sibling"

            # Keep the strongest link for each pair
            if pair not in best or _PRIORITY[kind] < _PRIORITY[best[pair].kind]:
                best[pair] = SiblingLink(
                    person_a_id=child_x,
                    person_b_id=child_y,
                    kind=kind,
                )

    return list(best.values())


def get_siblings_for(
    person_id: str,
    relationships: List[Relationship],
) -> List[SiblingLink]:
    """Return only the sibling links that involve *person_id*."""
    return [
        link for link in derive_siblings(relationships)
        if person_id in link.pair
    ]
