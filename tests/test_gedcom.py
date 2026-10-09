import os
import pytest
from pathlib import Path
from family_tree_app.db import Database
from family_tree_app.models import Person, Relationship
from family_tree_app.repositories import PersonRepository, RelationshipRepository
from family_tree_app.gedcom_io import import_gedcom, export_gedcom

def test_import_export_gedcom(tmp_path):
    schema_dir = Path(__file__).parent.parent / "src" / "family_tree_app" / "schema"
    
    db = Database(":memory:")
    db.run_migrations(schema_dir)
    
    person_repo = PersonRepository(db)
    rel_repo = RelationshipRepository(db)
    
    p1 = Person(name="John Doe", birth_date_str="1980-01-01")
    p2 = Person(name="Jane Smith", birth_date_str="1982-02-02")
    person_repo.create(p1)
    person_repo.create(p2)
    
    rel = Relationship(person_a_id=p1.id, person_b_id=p2.id, type="partnership:married", start_date_str="2005-05-05")
    rel_repo.create(rel)
    
    ged_path = tmp_path / "export.ged"
    
    # Export
    p_exp, r_exp = export_gedcom(str(ged_path), db)
    assert p_exp == 2
    assert r_exp == 1
    
    assert os.path.exists(ged_path)
    
    # Import into a new db
    db2 = Database(":memory:")
    db2.run_migrations(schema_dir)
    
    p_imp, r_imp = import_gedcom(str(ged_path), db2)
    assert p_imp == 2
    assert r_imp == 1
    
    person_repo2 = PersonRepository(db2)
    persons2 = person_repo2.get_all()
    assert len(persons2) == 2
    
    names = [p.name for p in persons2]
    assert "John Doe" in names
    assert "Jane Smith" in names
