-- A source is a citable reference (book, certificate, URL, etc.)
CREATE TABLE sources (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    publisher TEXT,
    publication_date TEXT,
    url TEXT,
    notes TEXT
);

-- Links a source to a specific fact on any entity.
-- Exactly one of person_id / event_id / relationship_id should be set.
-- field_name optionally narrows the citation to a specific field
-- (e.g. 'birth_date', 'occupation'); NULL means the source covers the
-- entity as a whole.
CREATE TABLE source_links (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    person_id TEXT,
    event_id TEXT,
    relationship_id TEXT,
    field_name TEXT,
    detail TEXT,
    FOREIGN KEY (source_id) REFERENCES sources(id),
    FOREIGN KEY (person_id) REFERENCES persons(id),
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (relationship_id) REFERENCES relationships(id)
);
