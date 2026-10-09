CREATE TABLE events (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    date_str TEXT,
    date TEXT,
    place TEXT,
    description TEXT,
    person_id TEXT,
    relationship_id TEXT,
    unverified BOOLEAN DEFAULT 0,
    FOREIGN KEY (person_id) REFERENCES persons(id),
    FOREIGN KEY (relationship_id) REFERENCES relationships(id)
);
