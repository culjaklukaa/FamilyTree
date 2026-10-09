from typing import List, Optional
from .models import Person, Relationship, Event, Media, Source, SourceLink
from .db import Database

class PersonRepository:
    def __init__(self, db: Database, enforce_privacy: bool = False):
        self.db = db
        self.enforce_privacy = enforce_privacy

    def _apply_privacy(self, person: Person) -> Person:
        if not self.enforce_privacy:
            return person
        from family_tree_app.privacy import apply_privacy
        return apply_privacy(person, force_public=not self.enforce_privacy)

    def create(self, person: Person) -> Person:
        query = """
            INSERT INTO persons (
                id, name, maiden_name, nicknames, 
                birth_date_str, birth_date, birth_place,
                death_date_str, death_date, death_place,
                photo_path, occupation, notes, custom_fields, privacy_settings, unverified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.connection.execute(query, (
            person.id, person.name, person.maiden_name, person.nicknames,
            person.birth_date_str, person.birth_date, person.birth_place,
            person.death_date_str, person.death_date, person.death_place,
            person.photo_path, person.occupation, person.notes, person.custom_fields,
            person.privacy_settings, person.unverified
        ))
        self.db.connection.commit()
        return self._apply_privacy(person)

    def _row_to_person(self, row) -> Person:
        p = Person(
            id=row["id"],
            name=row["name"],
            maiden_name=row["maiden_name"],
            nicknames=row["nicknames"],
            birth_date_str=row["birth_date_str"],
            birth_date=row["birth_date"],
            birth_place=row["birth_place"],
            death_date_str=row["death_date_str"],
            death_date=row["death_date"],
            death_place=row["death_place"],
            photo_path=row["photo_path"],
            occupation=row["occupation"],
            notes=row["notes"],
            custom_fields=row["custom_fields"],
            privacy_settings=row["privacy_settings"],
            unverified=bool(row["unverified"])
        )
        return self._apply_privacy(p)

    def get(self, person_id: str) -> Optional[Person]:
        query = "SELECT * FROM persons WHERE id = ?"
        cursor = self.db.connection.execute(query, (person_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_person(row)
        return None

    def get_all(self) -> List[Person]:
        query = "SELECT * FROM persons"
        cursor = self.db.connection.execute(query)
        return [self._row_to_person(row) for row in cursor.fetchall()]

    def search(self, name_query: Optional[str] = None, birth_place: Optional[str] = None, 
               birth_date_from: Optional[str] = None, birth_date_to: Optional[str] = None) -> List[Person]:
        conditions = []
        params = []
        
        if name_query:
            conditions.append("(name LIKE ? OR maiden_name LIKE ? OR nicknames LIKE ?)")
            q = f"%{name_query}%"
            params.extend([q, q, q])
            
        if birth_place:
            conditions.append("birth_place LIKE ?")
            params.append(f"%{birth_place}%")
            
        if birth_date_from:
            conditions.append("birth_date >= ?")
            params.append(birth_date_from)
            
        if birth_date_to:
            conditions.append("birth_date <= ?")
            params.append(birth_date_to)
            
        sql = "SELECT * FROM persons"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
            
        sql += " ORDER BY name"
        
        cursor = self.db.connection.execute(sql, tuple(params))
        # Note: the UI search tab handles filtering out fully redacted results based on query if needed
        return [self._row_to_person(row) for row in cursor.fetchall()]

    def update(self, person: Person) -> Person:
        if person._is_redacted:
            raise ValueError("Security Error: Attempted to save a redacted Person object. This would overwrite real data with 'Private'.")
            
        query = """
            UPDATE persons SET
                name = ?, maiden_name = ?, nicknames = ?,
                birth_date_str = ?, birth_date = ?, birth_place = ?,
                death_date_str = ?, death_date = ?, death_place = ?,
                photo_path = ?, occupation = ?, notes = ?, custom_fields = ?,
                privacy_settings = ?, unverified = ?
            WHERE id = ?
        """
        self.db.connection.execute(query, (
            person.name, person.maiden_name, person.nicknames,
            person.birth_date_str, person.birth_date, person.birth_place,
            person.death_date_str, person.death_date, person.death_place,
            person.photo_path, person.occupation, person.notes, person.custom_fields,
            person.privacy_settings, person.unverified, person.id
        ))
        self.db.connection.commit()
        return self._apply_privacy(person)

    def delete(self, person_id: str) -> None:
        query = "DELETE FROM persons WHERE id = ?"
        self.db.connection.execute(query, (person_id,))
        self.db.connection.commit()

class RelationshipRepository:
    def __init__(self, db: Database):
        self.db = db

    def create(self, rel: Relationship) -> Relationship:
        query = """
            INSERT INTO relationships (id, person_a_id, person_b_id, type, start_date_str, start_date, end_date_str, end_date, unverified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.connection.execute(query, (
            rel.id, rel.person_a_id, rel.person_b_id, rel.type,
            rel.start_date_str, rel.start_date, rel.end_date_str, rel.end_date, rel.unverified
        ))
        self.db.connection.commit()
        return rel

    def _row_to_relationship(self, row) -> Relationship:
        return Relationship(
            id=row["id"],
            person_a_id=row["person_a_id"],
            person_b_id=row["person_b_id"],
            type=row["type"],
            start_date_str=row["start_date_str"],
            start_date=row["start_date"],
            end_date_str=row["end_date_str"],
            end_date=row["end_date"],
            unverified=bool(row["unverified"])
        )

    def get(self, rel_id: str) -> Optional[Relationship]:
        query = "SELECT * FROM relationships WHERE id = ?"
        cursor = self.db.connection.execute(query, (rel_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_relationship(row)
        return None

    def get_by_person(self, person_id: str) -> List[Relationship]:
        query = "SELECT * FROM relationships WHERE person_a_id = ? OR person_b_id = ?"
        cursor = self.db.connection.execute(query, (person_id, person_id))
        return [self._row_to_relationship(row) for row in cursor.fetchall()]

    def get_all(self) -> List[Relationship]:
        query = "SELECT * FROM relationships"
        cursor = self.db.connection.execute(query)
        return [self._row_to_relationship(row) for row in cursor.fetchall()]

    def update(self, rel: Relationship) -> Relationship:
        query = """
            UPDATE relationships SET
                person_a_id = ?, person_b_id = ?, type = ?,
                start_date_str = ?, start_date = ?, end_date_str = ?, end_date = ?, unverified = ?
            WHERE id = ?
        """
        self.db.connection.execute(query, (
            rel.person_a_id, rel.person_b_id, rel.type,
            rel.start_date_str, rel.start_date, rel.end_date_str, rel.end_date, rel.unverified, rel.id
        ))
        self.db.connection.commit()
        return rel

    def delete(self, rel_id: str) -> None:
        query = "DELETE FROM relationships WHERE id = ?"
        self.db.connection.execute(query, (rel_id,))
        self.db.connection.commit()

class EventRepository:
    def __init__(self, db: Database):
        self.db = db

    def create(self, event: Event) -> Event:
        query = """
            INSERT INTO events (id, type, date_str, date, place, description, person_id, relationship_id, unverified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.connection.execute(query, (
            event.id, event.type, event.date_str, event.date, event.place, event.description,
            event.person_id, event.relationship_id, event.unverified
        ))
        self.db.connection.commit()
        return event

    def _row_to_event(self, row) -> Event:
        return Event(
            id=row["id"],
            type=row["type"],
            date_str=row["date_str"],
            date=row["date"],
            place=row["place"],
            description=row["description"],
            person_id=row["person_id"],
            relationship_id=row["relationship_id"],
            unverified=bool(row["unverified"])
        )

    def get(self, event_id: str) -> Optional[Event]:
        query = "SELECT * FROM events WHERE id = ?"
        cursor = self.db.connection.execute(query, (event_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_event(row)
        return None

    def get_by_person(self, person_id: str) -> List[Event]:
        query = "SELECT * FROM events WHERE person_id = ?"
        cursor = self.db.connection.execute(query, (person_id,))
        return [self._row_to_event(row) for row in cursor.fetchall()]

    def get_by_relationship(self, relationship_id: str) -> List[Event]:
        query = "SELECT * FROM events WHERE relationship_id = ?"
        cursor = self.db.connection.execute(query, (relationship_id,))
        return [self._row_to_event(row) for row in cursor.fetchall()]

    def update(self, event: Event) -> Event:
        query = """
            UPDATE events SET
                type = ?, date_str = ?, date = ?, place = ?, description = ?,
                person_id = ?, relationship_id = ?, unverified = ?
            WHERE id = ?
        """
        self.db.connection.execute(query, (
            event.type, event.date_str, event.date, event.place, event.description,
            event.person_id, event.relationship_id, event.unverified, event.id
        ))
        self.db.connection.commit()
        return event

    def delete(self, event_id: str) -> None:
        query = "DELETE FROM events WHERE id = ?"
        self.db.connection.execute(query, (event_id,))
        self.db.connection.commit()

class MediaRepository:
    def __init__(self, db: Database):
        self.db = db

    def create(self, media: Media) -> Media:
        query = """
            INSERT INTO media (id, file_path, thumbnail_path, title, description,
                               mime_type, file_size, person_id, event_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.connection.execute(query, (
            media.id, media.file_path, media.thumbnail_path, media.title,
            media.description, media.mime_type, media.file_size,
            media.person_id, media.event_id
        ))
        self.db.connection.commit()
        return media

    def _row_to_media(self, row) -> Media:
        return Media(
            id=row["id"],
            file_path=row["file_path"],
            thumbnail_path=row["thumbnail_path"],
            title=row["title"],
            description=row["description"],
            mime_type=row["mime_type"],
            file_size=row["file_size"],
            person_id=row["person_id"],
            event_id=row["event_id"]
        )

    def get(self, media_id: str) -> Optional[Media]:
        query = "SELECT * FROM media WHERE id = ?"
        cursor = self.db.connection.execute(query, (media_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_media(row)
        return None

    def get_by_person(self, person_id: str) -> List[Media]:
        query = "SELECT * FROM media WHERE person_id = ?"
        cursor = self.db.connection.execute(query, (person_id,))
        return [self._row_to_media(row) for row in cursor.fetchall()]

    def get_by_event(self, event_id: str) -> List[Media]:
        query = "SELECT * FROM media WHERE event_id = ?"
        cursor = self.db.connection.execute(query, (event_id,))
        return [self._row_to_media(row) for row in cursor.fetchall()]

    def update(self, media: Media) -> Media:
        query = """
            UPDATE media SET
                file_path = ?, thumbnail_path = ?, title = ?, description = ?,
                mime_type = ?, file_size = ?, person_id = ?, event_id = ?
            WHERE id = ?
        """
        self.db.connection.execute(query, (
            media.file_path, media.thumbnail_path, media.title, media.description,
            media.mime_type, media.file_size, media.person_id, media.event_id,
            media.id
        ))
        self.db.connection.commit()
        return media

    def delete(self, media_id: str) -> None:
        """Delete the DB record and remove the file + thumbnail from disk."""
        from pathlib import Path
        media = self.get(media_id)
        if media:
            data_dir = self.db.data_dir
            for rel_path in (media.file_path, media.thumbnail_path):
                if rel_path:
                    full = data_dir / rel_path
                    if full.is_file():
                        full.unlink(missing_ok=True)
        self.db.connection.execute("DELETE FROM media WHERE id = ?", (media_id,))
        self.db.connection.commit()

class SourceRepository:
    def __init__(self, db: Database):
        self.db = db

    def create(self, source: Source) -> Source:
        query = """
            INSERT INTO sources (id, title, author, publisher, publication_date, url, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self.db.connection.execute(query, (
            source.id, source.title, source.author, source.publisher,
            source.publication_date, source.url, source.notes
        ))
        self.db.connection.commit()
        return source

    def _row_to_source(self, row) -> Source:
        return Source(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            publisher=row["publisher"],
            publication_date=row["publication_date"],
            url=row["url"],
            notes=row["notes"]
        )

    def get(self, source_id: str) -> Optional[Source]:
        query = "SELECT * FROM sources WHERE id = ?"
        cursor = self.db.connection.execute(query, (source_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_source(row)
        return None

    def get_all(self) -> List[Source]:
        query = "SELECT * FROM sources ORDER BY title"
        cursor = self.db.connection.execute(query)
        return [self._row_to_source(row) for row in cursor.fetchall()]

    def update(self, source: Source) -> Source:
        query = """
            UPDATE sources SET
                title = ?, author = ?, publisher = ?,
                publication_date = ?, url = ?, notes = ?
            WHERE id = ?
        """
        self.db.connection.execute(query, (
            source.title, source.author, source.publisher,
            source.publication_date, source.url, source.notes, source.id
        ))
        self.db.connection.commit()
        return source

    def delete(self, source_id: str) -> None:
        # Also delete all links referencing this source
        self.db.connection.execute("DELETE FROM source_links WHERE source_id = ?", (source_id,))
        self.db.connection.execute("DELETE FROM sources WHERE id = ?", (source_id,))
        self.db.connection.commit()


class SourceLinkRepository:
    def __init__(self, db: Database):
        self.db = db

    def create(self, link: SourceLink) -> SourceLink:
        query = """
            INSERT INTO source_links (id, source_id, person_id, event_id, relationship_id, field_name, detail)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self.db.connection.execute(query, (
            link.id, link.source_id, link.person_id, link.event_id,
            link.relationship_id, link.field_name, link.detail
        ))
        self.db.connection.commit()
        return link

    def _row_to_link(self, row) -> SourceLink:
        return SourceLink(
            id=row["id"],
            source_id=row["source_id"],
            person_id=row["person_id"],
            event_id=row["event_id"],
            relationship_id=row["relationship_id"],
            field_name=row["field_name"],
            detail=row["detail"]
        )

    def get(self, link_id: str) -> Optional[SourceLink]:
        query = "SELECT * FROM source_links WHERE id = ?"
        cursor = self.db.connection.execute(query, (link_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_link(row)
        return None

    def get_by_person(self, person_id: str, field_name: str = None) -> List[SourceLink]:
        if field_name:
            query = "SELECT * FROM source_links WHERE person_id = ? AND field_name = ?"
            cursor = self.db.connection.execute(query, (person_id, field_name))
        else:
            query = "SELECT * FROM source_links WHERE person_id = ?"
            cursor = self.db.connection.execute(query, (person_id,))
        return [self._row_to_link(row) for row in cursor.fetchall()]

    def get_by_event(self, event_id: str) -> List[SourceLink]:
        query = "SELECT * FROM source_links WHERE event_id = ?"
        cursor = self.db.connection.execute(query, (event_id,))
        return [self._row_to_link(row) for row in cursor.fetchall()]

    def get_by_relationship(self, relationship_id: str) -> List[SourceLink]:
        query = "SELECT * FROM source_links WHERE relationship_id = ?"
        cursor = self.db.connection.execute(query, (relationship_id,))
        return [self._row_to_link(row) for row in cursor.fetchall()]

    def update(self, link: SourceLink) -> SourceLink:
        query = """
            UPDATE source_links SET
                source_id = ?, person_id = ?, event_id = ?,
                relationship_id = ?, field_name = ?, detail = ?
            WHERE id = ?
        """
        self.db.connection.execute(query, (
            link.source_id, link.person_id, link.event_id,
            link.relationship_id, link.field_name, link.detail, link.id
        ))
        self.db.connection.commit()
        return link

    def delete(self, link_id: str) -> None:
        query = "DELETE FROM source_links WHERE id = ?"
        self.db.connection.execute(query, (link_id,))
        self.db.connection.commit()
