import json
import copy
from typing import Optional, Dict, Any
from .models import Person

def get_privacy_settings(person: Person) -> Dict[str, Any]:
    """Parse the JSON privacy settings of a person."""
    if not person.privacy_settings:
        return {}
    try:
        return json.loads(person.privacy_settings)
    except json.JSONDecodeError:
        return {}

def apply_privacy(person: Person, force_public: bool = False) -> Person:
    """
    Returns a copy of the person with private fields redacted based on privacy_settings.
    If force_public is True, returns the person as-is.
    """
    if force_public:
        return person
        
    settings = get_privacy_settings(person)
    if not settings:
        return person
        
    p = copy.deepcopy(person)
    
    # 1. Whole-person privacy (hide completely)
    if settings.get("is_private") or settings.get("is_living"):
        # For living or strictly private people, redact everything except ID
        p.name = "Private" if settings.get("is_private") else "Living"
        p.maiden_name = None
        p.nicknames = None
        p.birth_date_str = None
        p.birth_date = None
        p.birth_place = None
        p.death_date_str = None
        p.death_date = None
        p.death_place = None
        p.photo_path = None
        p.occupation = None
        p.notes = None
        p.custom_fields = None
        p._is_redacted = True
        return p
        
    # 2. Field-level privacy
    if settings.get("hide_notes"):
        p.notes = None
        
    if settings.get("hide_birth"):
        p.birth_date_str = None
        p.birth_date = None
        p.birth_place = None
        
    if settings.get("hide_death"):
        p.death_date_str = None
        p.death_date = None
        p.death_place = None
        
    # Generalized hidden fields array
    hidden_fields = settings.get("hidden_fields", [])
    for field in hidden_fields:
        if hasattr(p, field) and field != "id":
            setattr(p, field, None)
            
    p._is_redacted = True
    return p
