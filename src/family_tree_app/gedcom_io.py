import re
from typing import Dict, List, Tuple
from family_tree_app.db import Database
from family_tree_app.models import Person, Relationship
from family_tree_app.repositories import PersonRepository, RelationshipRepository

def import_gedcom(file_path: str, db: Database) -> Tuple[int, int]:
    """Imports a GEDCOM file into the database. Returns (persons_added, relationships_added)."""
    person_repo = PersonRepository(db)
    rel_repo = RelationshipRepository(db)

    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    
    current_record = None
    records = []
    
    # Simple parse
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split(' ', 2)
        if len(parts) < 2:
            continue
        level = parts[0]
        
        if level == '0':
            if len(parts) >= 3 and (parts[2] == 'INDI' or parts[2] == 'FAM'):
                current_record = {'type': parts[2], 'id': parts[1], 'children': []}
                records.append(current_record)
            else:
                current_record = None
        elif current_record is not None:
            tag = parts[1]
            val = parts[2] if len(parts) > 2 else ""
            current_record['children'].append((int(level), tag, val))
    
    indi_map = {} # gedcom id -> db id
    persons_added = 0
    rels_added = 0
    
    for r in records:
        if r['type'] == 'INDI':
            p = Person(name="Unknown")
            indi_map[r['id']] = p.id
            
            current_tag = None
            for level, tag, val in r['children']:
                if level == 1:
                    current_tag = tag
                    if tag == 'NAME':
                        p.name = val.replace('/', '').strip()
                elif level == 2:
                    if current_tag == 'BIRT':
                        if tag == 'DATE': p.birth_date_str = val
                        elif tag == 'PLAC': p.birth_place = val
                    elif current_tag == 'DEAT':
                        if tag == 'DATE': p.death_date_str = val
                        elif tag == 'PLAC': p.death_place = val
            person_repo.create(p)
            persons_added += 1
            
    for r in records:
        if r['type'] == 'FAM':
            husb = None
            wife = None
            children = []
            marr_date = None
            
            current_tag = None
            for level, tag, val in r['children']:
                if level == 1:
                    current_tag = tag
                    if tag == 'HUSB': husb = val
                    elif tag == 'WIFE': wife = val
                    elif tag == 'CHIL': children.append(val)
                elif level == 2:
                    if current_tag == 'MARR' and tag == 'DATE':
                        marr_date = val
                        
            husb_id = indi_map.get(husb)
            wife_id = indi_map.get(wife)
            
            parents = []
            if husb_id and wife_id:
                rel = Relationship(person_a_id=husb_id, person_b_id=wife_id, type="partnership:married")
                if marr_date:
                    rel.start_date_str = marr_date
                rel_repo.create(rel)
                rels_added += 1
                parents = [husb_id, wife_id]
            elif husb_id:
                parents = [husb_id]
            elif wife_id:
                parents = [wife_id]
                
            for chil in children:
                chil_id = indi_map.get(chil)
                if chil_id:
                    for pid in parents:
                        rel = Relationship(person_a_id=pid, person_b_id=chil_id, type="parent-child:biological")
                        rel_repo.create(rel)
                        rels_added += 1

    return persons_added, rels_added


def export_gedcom(file_path: str, db: Database, force_public: bool = False) -> Tuple[int, int]:
    """Exports the database to a GEDCOM file. Returns (persons_exported, relationships_exported)."""
    person_repo = PersonRepository(db, enforce_privacy=not force_public)
    rel_repo = RelationshipRepository(db)
    
    persons = person_repo.get_all()
    # Assuming we add get_all() to rel_repo
    rels = rel_repo.get_all()
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("0 HEAD\n")
        f.write("1 SOUR FamilyTreeApp\n")
        f.write("1 CHAR UTF-8\n")
        
        for p in persons:
            p_id = p.id.replace('-', '')
            f.write(f"0 @I{p_id}@ INDI\n")
            
            # format name with slashes around surname
            parts = p.name.rsplit(' ', 1)
            if len(parts) == 2:
                name_str = f"{parts[0]} /{parts[1]}/"
            else:
                name_str = f"{p.name} //"
            f.write(f"1 NAME {name_str}\n")
            
            if p.birth_date_str or p.birth_place:
                f.write("1 BIRT\n")
                if p.birth_date_str: f.write(f"2 DATE {p.birth_date_str}\n")
                if p.birth_place: f.write(f"2 PLAC {p.birth_place}\n")
            
            if p.death_date_str or p.death_place:
                f.write("1 DEAT\n")
                if p.death_date_str: f.write(f"2 DATE {p.death_date_str}\n")
                if p.death_place: f.write(f"2 PLAC {p.death_place}\n")
                
        # Group families
        fam_index = 1
        partnerships = [r for r in rels if r.type.startswith("partnership")]
        
        children_by_parent = {}
        for r in rels:
            if r.type.startswith("parent-child"):
                children_by_parent.setdefault(r.person_a_id, []).append(r.person_b_id)
                
        # We also need to group single parents if they have children but no partner?
        # A simple export can just export partnerships and their common children
        for rel in partnerships:
            f.write(f"0 @F{fam_index}@ FAM\n")
            f.write(f"1 HUSB @I{rel.person_a_id.replace('-', '')}@\n")
            f.write(f"1 WIFE @I{rel.person_b_id.replace('-', '')}@\n")
            if rel.start_date_str:
                f.write("1 MARR\n")
                f.write(f"2 DATE {rel.start_date_str}\n")
                
            children_a = set(children_by_parent.get(rel.person_a_id, []))
            children_b = set(children_by_parent.get(rel.person_b_id, []))
            common_children = children_a.intersection(children_b)
            for c in common_children:
                f.write(f"1 CHIL @I{c.replace('-', '')}@\n")
            fam_index += 1
            
        f.write("0 TRLR\n")
        
    return len(persons), len(rels)
