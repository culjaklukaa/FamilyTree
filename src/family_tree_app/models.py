from dataclasses import dataclass, field
from typing import Optional
import uuid

def generate_id() -> str:
    """Generate a unique ID for new records."""
    return str(uuid.uuid4())

@dataclass
class Person:
    name: str
    maiden_name: Optional[str] = None
    nicknames: Optional[str] = None
    birth_date_str: Optional[str] = None
    birth_date: Optional[str] = None # ISO format YYYY-MM-DD
    birth_place: Optional[str] = None
    death_date_str: Optional[str] = None
    death_date: Optional[str] = None
    death_place: Optional[str] = None
    photo_path: Optional[str] = None
    occupation: Optional[str] = None
    notes: Optional[str] = None
    custom_fields: Optional[str] = None
    privacy_settings: Optional[str] = None # JSON string for field- or person-level privacy
    unverified: bool = False
    _is_redacted: bool = False # Internal flag to prevent saving redacted data
    id: str = field(default_factory=generate_id)

@dataclass
class Relationship:
    person_a_id: str
    person_b_id: str
    type: str # e.g., 'parent-child', 'partnership'
    start_date_str: Optional[str] = None
    start_date: Optional[str] = None
    end_date_str: Optional[str] = None
    end_date: Optional[str] = None
    unverified: bool = False
    id: str = field(default_factory=generate_id)

@dataclass
class Event:
    type: str # e.g. 'birth', 'death', 'marriage', 'custom'
    date_str: Optional[str] = None
    date: Optional[str] = None # ISO format YYYY-MM-DD
    place: Optional[str] = None
    description: Optional[str] = None
    person_id: Optional[str] = None
    relationship_id: Optional[str] = None
    unverified: bool = False
    id: str = field(default_factory=generate_id)

@dataclass
class Media:
    file_path: str
    thumbnail_path: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    person_id: Optional[str] = None
    event_id: Optional[str] = None
    id: str = field(default_factory=generate_id)

@dataclass
class Source:
    title: str
    author: Optional[str] = None
    publisher: Optional[str] = None
    publication_date: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None
    id: str = field(default_factory=generate_id)

@dataclass
class SourceLink:
    source_id: str
    person_id: Optional[str] = None
    event_id: Optional[str] = None
    relationship_id: Optional[str] = None
    field_name: Optional[str] = None
    detail: Optional[str] = None
    id: str = field(default_factory=generate_id)
