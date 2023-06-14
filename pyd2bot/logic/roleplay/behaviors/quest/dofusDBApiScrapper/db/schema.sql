CREATE TABLE Maps_POIs (
    map_id REAL,
    poi_id INTEGER,
    PRIMARY KEY (map_id, poi_id)
);

CREATE TABLE ProcessedMaps (
    map_id REAL,
    x INTEGER,
    y INTEGER,
    direction INTEGER CHECK(direction IN (0, 2, 4, 6)),
    PRIMARY KEY (map_id, x, y, direction)
);