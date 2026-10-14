PRAGMA foreign_keys = ON;
CREATE TABLE snapshots (
  snapshot_id TEXT PRIMARY KEY,
  archive_id TEXT NOT NULL,
  sequence INTEGER NOT NULL UNIQUE,
  generated_at TEXT NOT NULL,
  wire_sha256 TEXT NOT NULL
);
CREATE TABLE active_snapshot (
  singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
  snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
  sequence INTEGER NOT NULL
);
CREATE TABLE issue_versions (
  issue_id TEXT NOT NULL,
  revision TEXT NOT NULL,
  payload TEXT NOT NULL,
  PRIMARY KEY(issue_id, revision)
);
CREATE TABLE snapshot_items (
  snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
  issue_id TEXT NOT NULL,
  revision TEXT NOT NULL,
  PRIMARY KEY(snapshot_id, issue_id),
  FOREIGN KEY(issue_id, revision) REFERENCES issue_versions(issue_id, revision)
);
CREATE TABLE decisions (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  decision_id TEXT NOT NULL UNIQUE,
  issue_id TEXT NOT NULL,
  revision TEXT NOT NULL,
  previous_decision_id TEXT,
  snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
  sha256 TEXT NOT NULL,
  payload TEXT NOT NULL,
  FOREIGN KEY(issue_id, revision) REFERENCES issue_versions(issue_id, revision)
);
CREATE INDEX decisions_issue ON decisions(issue_id, seq);
CREATE TABLE receipts (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  sha256 TEXT NOT NULL UNIQUE,
  decision_id TEXT NOT NULL REFERENCES decisions(decision_id),
  status TEXT NOT NULL CHECK(status IN ('applied','recorded','deferred','stale','invalid','completed')),
  payload TEXT NOT NULL
);
CREATE INDEX receipts_decision ON receipts(decision_id, seq);
CREATE TRIGGER version_content BEFORE INSERT ON issue_versions BEGIN
  SELECT RAISE(ABORT, 'Issue revision has different content')
  WHERE EXISTS (SELECT 1 FROM issue_versions WHERE issue_id=NEW.issue_id AND revision=NEW.revision AND payload!=NEW.payload);
END;
CREATE TRIGGER decision_revision BEFORE INSERT ON decisions BEGIN
  SELECT RAISE(ABORT, 'Issue revision changed') WHERE NOT EXISTS (
    SELECT 1 FROM snapshot_items i JOIN active_snapshot a ON a.snapshot_id=i.snapshot_id
    WHERE i.issue_id=NEW.issue_id AND i.revision=NEW.revision AND i.snapshot_id=NEW.snapshot_id
  );
  SELECT RAISE(ABORT, 'Another reviewer submitted a decision') WHERE COALESCE(NEW.previous_decision_id,'') != COALESCE((
    SELECT decision_id FROM decisions WHERE issue_id=NEW.issue_id ORDER BY seq DESC LIMIT 1
  ),'');
  SELECT RAISE(ABORT, 'Decision application is pending') WHERE NEW.previous_decision_id IS NOT NULL AND COALESCE((
    SELECT status FROM receipts WHERE decision_id=NEW.previous_decision_id ORDER BY seq DESC LIMIT 1
  ),'submitted') NOT IN ('completed','deferred','stale','invalid');
END;
CREATE TRIGGER receipt_transition BEFORE INSERT ON receipts BEGIN
  SELECT RAISE(ABORT, 'Receipt transition is invalid') WHERE EXISTS(SELECT 1 FROM receipts WHERE decision_id=NEW.decision_id)
    AND NOT (NEW.status='completed' AND (
      SELECT status FROM receipts WHERE decision_id=NEW.decision_id ORDER BY seq DESC LIMIT 1
    ) IN ('recorded','applied'));
  SELECT RAISE(ABORT, 'Application receipt is required') WHERE NOT EXISTS(SELECT 1 FROM receipts WHERE decision_id=NEW.decision_id)
    AND NEW.status='completed';
END;
CREATE TRIGGER decisions_no_update BEFORE UPDATE ON decisions BEGIN SELECT RAISE(ABORT,'Decisions are immutable'); END;
CREATE TRIGGER decisions_no_delete BEFORE DELETE ON decisions BEGIN SELECT RAISE(ABORT,'Decisions are immutable'); END;
CREATE TRIGGER receipts_no_update BEFORE UPDATE ON receipts BEGIN SELECT RAISE(ABORT,'Receipts are immutable'); END;
CREATE TRIGGER receipts_no_delete BEFORE DELETE ON receipts BEGIN SELECT RAISE(ABORT,'Receipts are immutable'); END;
CREATE TRIGGER versions_no_update BEFORE UPDATE ON issue_versions BEGIN SELECT RAISE(ABORT,'Issue versions are immutable'); END;
CREATE TRIGGER versions_no_delete BEFORE DELETE ON issue_versions BEGIN SELECT RAISE(ABORT,'Issue versions are immutable'); END;
CREATE TRIGGER snapshots_no_update BEFORE UPDATE ON snapshots BEGIN SELECT RAISE(ABORT,'Snapshots are immutable'); END;
CREATE TRIGGER snapshots_no_delete BEFORE DELETE ON snapshots BEGIN SELECT RAISE(ABORT,'Snapshots are immutable'); END;
CREATE TRIGGER items_no_update BEFORE UPDATE ON snapshot_items BEGIN SELECT RAISE(ABORT,'Snapshot membership is immutable'); END;
CREATE TRIGGER items_no_delete BEFORE DELETE ON snapshot_items BEGIN SELECT RAISE(ABORT,'Snapshot membership is immutable'); END;
