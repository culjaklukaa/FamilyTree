import pytest
from pathlib import Path
from family_tree_app.db import Database
from family_tree_app.models import Person, Relationship, Event, Source, SourceLink, Media
from family_tree_app.repositories import (
    PersonRepository, RelationshipRepository, EventRepository,
    SourceRepository, SourceLinkRepository, MediaRepository
)

@pytest.fixture
def db():
    database = Database(":memory:")
    schema_dir = Path(__file__).parent.parent / "src" / "family_tree_app" / "schema"
    database.run_migrations(schema_dir)
    yield database
    database.close()

def test_person_repository(db):
    repo = PersonRepository(db)
    
    person = Person(name="Eleanor Hart", birth_date_str="circa 1920")
    created = repo.create(person)
    
    assert created.id is not None
    
    fetched = repo.get(created.id)
    assert fetched is not None
    assert fetched.name == "Eleanor Hart"
    assert fetched.birth_date_str == "circa 1920"
    
    all_persons = repo.get_all()
    assert len(all_persons) == 1
    
    # Test update
    fetched.name = "Eleanor Smith"
    fetched.maiden_name = "Hart"
    updated = repo.update(fetched)
    assert updated.name == "Eleanor Smith"
    assert updated.maiden_name == "Hart"
    
    re_fetched = repo.get(created.id)
    assert re_fetched.name == "Eleanor Smith"
    assert re_fetched.maiden_name == "Hart"
    
    # Test delete
    repo.delete(created.id)
    assert repo.get(created.id) is None
    assert len(repo.get_all()) == 0

def test_relationship_repository(db):
    p_repo = PersonRepository(db)
    r_repo = RelationshipRepository(db)
    
    p1 = p_repo.create(Person(name="Walter Hart"))
    p2 = p_repo.create(Person(name="Eleanor Hart"))
    
    rel = Relationship(
        person_a_id=p1.id,
        person_b_id=p2.id,
        type="partnership",
        start_date_str="1945"
    )
    r_repo.create(rel)
    
    rels = r_repo.get_by_person(p1.id)
    assert len(rels) == 1
    assert rels[0].type == "partnership"
    assert rels[0].person_b_id == p2.id
    
    # Test get
    fetched = r_repo.get(rel.id)
    assert fetched is not None
    assert fetched.type == "partnership"
    
    # Test update
    fetched.type = "partnership:married"
    r_repo.update(fetched)
    updated = r_repo.get(rel.id)
    assert updated.type == "partnership:married"
    
    # Test delete
    r_repo.delete(rel.id)
    assert r_repo.get(rel.id) is None
    assert len(r_repo.get_by_person(p1.id)) == 0

def test_event_repository(db):
    p_repo = PersonRepository(db)
    e_repo = EventRepository(db)
    
    p1 = p_repo.create(Person(name="Walter Hart"))
    
    event = Event(
        type="birth",
        date_str="Oct 12, 1920",
        place="London",
        person_id=p1.id
    )
    e_repo.create(event)
    
    events = e_repo.get_by_person(p1.id)
    assert len(events) == 1
    assert events[0].type == "birth"
    assert events[0].place == "London"
    
    # Test get
    fetched = e_repo.get(event.id)
    assert fetched is not None
    assert fetched.type == "birth"
    
    # Test update
    fetched.place = "New York"
    e_repo.update(fetched)
    updated = e_repo.get(event.id)
    assert updated.place == "New York"
    
    # Test delete
    e_repo.delete(event.id)
    assert e_repo.get(event.id) is None
    assert len(e_repo.get_by_person(p1.id)) == 0


def test_source_repository(db):
    s_repo = SourceRepository(db)

    src = Source(title="Birth Certificate", author="City of London")
    created = s_repo.create(src)
    assert created.id is not None

    fetched = s_repo.get(created.id)
    assert fetched is not None
    assert fetched.title == "Birth Certificate"
    assert fetched.author == "City of London"

    # Test get_all
    s_repo.create(Source(title="Census 1921"))
    all_sources = s_repo.get_all()
    assert len(all_sources) == 2

    # Test update
    fetched.title = "Death Certificate"
    s_repo.update(fetched)
    updated = s_repo.get(created.id)
    assert updated.title == "Death Certificate"

    # Test delete
    s_repo.delete(created.id)
    assert s_repo.get(created.id) is None


def test_source_link_repository(db):
    p_repo = PersonRepository(db)
    s_repo = SourceRepository(db)
    sl_repo = SourceLinkRepository(db)

    person = p_repo.create(Person(name="Walter Hart"))
    source = s_repo.create(Source(title="Birth Certificate"))

    # Link source to person's birth_date field
    link = SourceLink(
        source_id=source.id,
        person_id=person.id,
        field_name="birth_date",
        detail="entry #12",
    )
    sl_repo.create(link)

    # Retrieve by person
    links = sl_repo.get_by_person(person.id)
    assert len(links) == 1
    assert links[0].field_name == "birth_date"
    assert links[0].detail == "entry #12"

    # Retrieve by person + field
    links_filtered = sl_repo.get_by_person(person.id, field_name="birth_date")
    assert len(links_filtered) == 1
    links_other = sl_repo.get_by_person(person.id, field_name="name")
    assert len(links_other) == 0

    # Test update
    fetched = sl_repo.get(link.id)
    fetched.detail = "page 5"
    sl_repo.update(fetched)
    updated = sl_repo.get(link.id)
    assert updated.detail == "page 5"

    # Test delete
    sl_repo.delete(link.id)
    assert sl_repo.get(link.id) is None
    assert len(sl_repo.get_by_person(person.id)) == 0


def test_source_cascade_delete(db):
    """Deleting a source should also remove all its links."""
    p_repo = PersonRepository(db)
    s_repo = SourceRepository(db)
    sl_repo = SourceLinkRepository(db)

    person = p_repo.create(Person(name="Eleanor Hart"))
    source = s_repo.create(Source(title="Parish Register"))

    sl_repo.create(SourceLink(source_id=source.id, person_id=person.id, field_name="birth_date"))
    sl_repo.create(SourceLink(source_id=source.id, person_id=person.id, field_name="name"))

    assert len(sl_repo.get_by_person(person.id)) == 2

    s_repo.delete(source.id)
    assert s_repo.get(source.id) is None
    assert len(sl_repo.get_by_person(person.id)) == 0


def test_source_link_to_event(db):
    p_repo = PersonRepository(db)
    e_repo = EventRepository(db)
    s_repo = SourceRepository(db)
    sl_repo = SourceLinkRepository(db)

    person = p_repo.create(Person(name="Walter Hart"))
    event = e_repo.create(Event(type="marriage", person_id=person.id, place="London"))
    source = s_repo.create(Source(title="Marriage Certificate"))

    sl_repo.create(SourceLink(source_id=source.id, event_id=event.id, detail="page 3"))

    links = sl_repo.get_by_event(event.id)
    assert len(links) == 1
    assert links[0].detail == "page 3"


def test_media_repository_with_metadata_and_cleanup(db):
    m_repo = MediaRepository(db)
    
    # Create fake files to test cleanup
    data_dir = db.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = "media/test.jpg"
    thumb_path = "media/thumbnails/thumb_test.jpg"
    
    (data_dir / "media").mkdir(exist_ok=True)
    (data_dir / "media" / "thumbnails").mkdir(exist_ok=True)
    
    (data_dir / file_path).write_text("fake image data")
    (data_dir / thumb_path).write_text("fake thumb data")
    
    media = Media(
        file_path=file_path,
        thumbnail_path=thumb_path,
        title="Test Image",
        mime_type="image/jpeg",
        file_size=15
    )
    
    created = m_repo.create(media)
    assert created.id is not None
    
    fetched = m_repo.get(created.id)
    assert fetched.mime_type == "image/jpeg"
    assert fetched.file_size == 15
    
    # Test update
    fetched.mime_type = "image/png"
    m_repo.update(fetched)
    updated = m_repo.get(created.id)
    assert updated.mime_type == "image/png"
    
    # Verify files exist before delete
    assert (data_dir / file_path).exists()
    assert (data_dir / thumb_path).exists()
    
    # Test delete (should remove DB record and files)
    m_repo.delete(created.id)
    assert m_repo.get(created.id) is None
    
    # Verify files were cleaned up
    assert not (data_dir / file_path).exists()
    assert not (data_dir / thumb_path).exists()

def test_person_search(db):
    repo = PersonRepository(db)
    repo.create(Person(name="Walter Hart", birth_place="London", birth_date="1920-05-01"))
    repo.create(Person(name="Eleanor Hart", birth_place="London", birth_date="1922-08-15"))
    repo.create(Person(name="George Smith", birth_place="New York", birth_date="1910-01-10"))

    # Search by name
    assert len(repo.search(name_query="Hart")) == 2
    assert len(repo.search(name_query="Smith")) == 1

    # Search by birthplace
    assert len(repo.search(birth_place="London")) == 2
    assert len(repo.search(birth_place="York")) == 1

    # Search by date range
    assert len(repo.search(birth_date_from="1920-01-01", birth_date_to="1921-12-31")) == 1
    assert len(repo.search(birth_date_from="1920-01-01")) == 2

    # Combined search
    assert len(repo.search(name_query="Hart", birth_place="London")) == 2
    assert len(repo.search(name_query="George", birth_place="London")) == 0
