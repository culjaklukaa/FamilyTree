import pytest
from pathlib import Path
from family_tree_app.db import Database
from family_tree_app.models import Person, Relationship
from family_tree_app.repositories import PersonRepository, RelationshipRepository

def test_sqlite_roundtrip(tmp_path):
    """
    Verify that data saves to a SQLite file and can be reliably loaded
    back on a fresh connection (simulating app restart).
    """
    db_file = tmp_path / "test_family_tree.db"
    schema_dir = Path(__file__).parent.parent / "src" / "family_tree_app" / "schema"

    # 1. Open DB, run migrations, write data
    db_write = Database(db_file)
    db_write.run_migrations(schema_dir)
    
    p_repo_write = PersonRepository(db_write)
    r_repo_write = RelationshipRepository(db_write)
    
    # Create two people
    p1 = p_repo_write.create(Person(name="John Doe", birth_date_str="1950-01-01"))
    p2 = p_repo_write.create(Person(name="Jane Doe", birth_date_str="1955-05-05"))
    
    # Create a relationship
    r1 = r_repo_write.create(Relationship(
        person_a_id=p1.id,
        person_b_id=p2.id,
        type="partnership:married",
        start_date_str="1975"
    ))
    
    # Close connection
    db_write.close()
    
    # 2. Open DB with a fresh connection (like restarting the app)
    db_read = Database(db_file)
    p_repo_read = PersonRepository(db_read)
    r_repo_read = RelationshipRepository(db_read)
    
    # Read data back
    persons = p_repo_read.get_all()
    assert len(persons) == 2
    
    # Verify Person 1
    loaded_p1 = p_repo_read.get(p1.id)
    assert loaded_p1 is not None
    assert loaded_p1.name == "John Doe"
    assert loaded_p1.birth_date_str == "1950-01-01"
    
    # Verify Person 2
    loaded_p2 = p_repo_read.get(p2.id)
    assert loaded_p2 is not None
    assert loaded_p2.name == "Jane Doe"
    
    # Verify Relationship
    rels = r_repo_read.get_by_person(loaded_p1.id)
    assert len(rels) == 1
    assert rels[0].type == "partnership:married"
    assert rels[0].person_b_id == loaded_p2.id
    
    db_read.close()
