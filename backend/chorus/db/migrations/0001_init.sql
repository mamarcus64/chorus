CREATE TABLE schema_migrations (
  version TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE users (
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL UNIQUE COLLATE NOCASE,
  password_hash TEXT NOT NULL,
  is_admin INTEGER NOT NULL DEFAULT 0 CHECK (is_admin IN (0, 1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE tasks (
  id TEXT PRIMARY KEY,
  code_key TEXT NOT NULL,
  code_version INTEGER NOT NULL,
  name TEXT NOT NULL UNIQUE,
  config TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(config)),
  archived_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE partitions (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT,
  name TEXT NOT NULL,
  description TEXT,
  config TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(config)),
  assignment TEXT NOT NULL DEFAULT 'everyone' CHECK (assignment IN ('everyone', 'selected')),
  archived_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (task_id, name)
);

CREATE TABLE items (
  id TEXT PRIMARY KEY,
  partition_id TEXT NOT NULL REFERENCES partitions(id) ON DELETE RESTRICT,
  ordinal INTEGER NOT NULL,
  kind TEXT NOT NULL,
  locator TEXT NOT NULL CHECK (json_valid(locator)),
  features TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(features)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (partition_id, ordinal)
);

CREATE TABLE partition_assignees (
  partition_id TEXT NOT NULL REFERENCES partitions(id) ON DELETE RESTRICT,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (partition_id, user_id)
);

CREATE TABLE partition_progress (
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  partition_id TEXT NOT NULL REFERENCES partitions(id) ON DELETE RESTRICT,
  status TEXT NOT NULL CHECK (status IN ('todo', 'done')),
  done_via TEXT CHECK (done_via IN ('answers', 'marked')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (user_id, partition_id),
  CHECK ((status = 'done') = (done_via IS NOT NULL))
);

CREATE TABLE annotations (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  item_id TEXT NOT NULL REFERENCES items(id) ON DELETE RESTRICT,
  value TEXT NOT NULL CHECK (json_valid(value)),
  elapsed_ms INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (user_id, item_id)
);

CREATE INDEX idx_annotations_item ON annotations(item_id);
CREATE INDEX idx_progress_partition ON partition_progress(partition_id);
