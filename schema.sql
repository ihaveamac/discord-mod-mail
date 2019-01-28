DROP TABLE IF EXISTS ignored;

CREATE TABLE ignored (
  user_id INTEGER UNIQUE,
  quiet INTEGER NOT NULL,
  reason TEXT
);
