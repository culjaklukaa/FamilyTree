CREATE TABLE persons (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    birth_date_str TEXT,
    birth_date TEXT,
    death_date_str TEXT,
    death_date TEXT,
    notes TEXT,
    unverified BOOLEAN DEFAULT 0
);

CREATE TABLE relationships (
    id TEXT PRIMARY KEY,
    person_a_id TEXT NOT NULL,
    person_b_id TEXT NOT NULL,
    type TEXT NOT NULL,
    start_date_str TEXT,
    start_date TEXT,
    end_date_str TEXT,
    end_date TEXT,
    unverified BOOLEAN DEFAULT 0,
    FOREIGN KEY (person_a_id) REFERENCES persons(id),
    FOREIGN KEY (person_b_id) REFERENCES persons(id)
);
