CREATE TABLE media (
    id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    thumbnail_path TEXT,
    title TEXT,
    description TEXT,
    person_id TEXT,
    event_id TEXT,
    FOREIGN KEY (person_id) REFERENCES persons(id),
    FOREIGN KEY (event_id) REFERENCES events(id)
);
