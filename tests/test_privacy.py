import json
from family_tree_app.models import Person
from family_tree_app.privacy import apply_privacy

def test_apply_privacy_no_settings():
    p = Person(name="John Doe", notes="Some notes")
    p_safe = apply_privacy(p)
    assert p_safe.name == "John Doe"
    assert p_safe.notes == "Some notes"

def test_apply_privacy_is_private():
    settings = {"is_private": True}
    p = Person(name="John Doe", birth_date_str="1980-01-01", notes="Secret", privacy_settings=json.dumps(settings))
    p_safe = apply_privacy(p)
    assert p_safe.name == "Private"
    assert p_safe.birth_date_str is None
    assert p_safe.notes is None

def test_apply_privacy_is_living():
    settings = {"is_living": True}
    p = Person(name="John Doe", birth_date_str="2000-01-01", privacy_settings=json.dumps(settings))
    p_safe = apply_privacy(p)
    assert p_safe.name == "Living"
    assert p_safe.birth_date_str is None

def test_apply_privacy_field_level():
    settings = {"hide_notes": True, "hide_birth": True}
    p = Person(name="John Doe", birth_date_str="1980-01-01", death_date_str="2050-01-01", notes="Secret", privacy_settings=json.dumps(settings))
    p_safe = apply_privacy(p)
    assert p_safe.name == "John Doe"
    assert p_safe.birth_date_str is None
    assert p_safe.death_date_str == "2050-01-01"
    assert p_safe.notes is None

def test_apply_privacy_force_public():
    settings = {"is_private": True}
    p = Person(name="John Doe", birth_date_str="1980-01-01", notes="Secret", privacy_settings=json.dumps(settings))
    p_safe = apply_privacy(p, force_public=True)
    assert p_safe.name == "John Doe"
    assert p_safe.birth_date_str == "1980-01-01"
