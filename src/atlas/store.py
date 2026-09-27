"""An insert-only, hash-chained ledger plus content-addressed source objects."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from .util import canonical, digest, stamp, atomic_write, uid


class Store:
    def __init__(self, home: Path | str):
        self.home = Path(home)
        self.home.mkdir(parents=True,exist_ok=True)
        self.db = sqlite3.connect(self.home / "ledger.sqlite", timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=DELETE")
        self.db.execute("""CREATE TABLE IF NOT EXISTS records (
            seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
            kind TEXT NOT NULL, recorded_at TEXT NOT NULL, payload TEXT NOT NULL,
            previous_hash TEXT NOT NULL, record_hash TEXT NOT NULL)""")
        self.db.execute("CREATE INDEX IF NOT EXISTS records_kind_date ON records(kind,recorded_at)")
        self.db.execute("""CREATE TRIGGER IF NOT EXISTS immutable_update BEFORE UPDATE ON records
            BEGIN SELECT RAISE(ABORT, 'ledger records are immutable'); END""")
        self.db.execute("""CREATE TRIGGER IF NOT EXISTS immutable_delete BEFORE DELETE ON records
            BEGIN SELECT RAISE(ABORT, 'ledger records are immutable'); END""")
        self.db.commit()

    def close(self):
        self.db.close()

    def append(self, kind: str, payload: dict, recorded_at: str, record_id: str | None = None) -> str:
        at = stamp(recorded_at)
        record_id = record_id or uid(kind, at, payload)
        encoded = canonical(payload)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            old = self.db.execute("SELECT * FROM records WHERE id=?", (record_id,)).fetchone()
            if old:
                if old["payload"] != encoded or old["kind"] != kind:
                    raise ValueError("An immutable record identity has different content")
                return record_id
            last = self.db.execute("SELECT record_hash FROM records ORDER BY seq DESC LIMIT 1").fetchone()
            prev = last[0] if last else "0"*64
            h = digest([record_id,kind,at,payload,prev])
            self.db.execute("INSERT INTO records(id,kind,recorded_at,payload,previous_hash,record_hash) VALUES(?,?,?,?,?,?)",
                            (record_id,kind,at,encoded,prev,h))
        return record_id

    def records(self, kind: str | None = None, as_of: str | None = None) -> list[dict]:
        clauses, args = [], []
        if kind:
            clauses.append("kind=?"); args.append(kind)
        if as_of:
            clauses.append("recorded_at<=?"); args.append(stamp(as_of))
        sql = "SELECT * FROM records" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY seq"
        return [{**dict(row), "payload":json.loads(row["payload"])} for row in self.db.execute(sql,args)]

    def get(self, record_id: str) -> dict:
        row = self.db.execute("SELECT * FROM records WHERE id=?",(record_id,)).fetchone()
        if row is None:
            raise KeyError(record_id)
        return {**dict(row), "payload":json.loads(row["payload"])}

    def has(self, record_id: str) -> bool:
        return self.db.execute("SELECT 1 FROM records WHERE id=?",(record_id,)).fetchone() is not None

    def object(self, data: bytes, suffix: str) -> str:
        name = f"objects/{digest(data)}.{suffix}"
        path = self.home / name
        if not path.exists():
            atomic_write(path,data)
        return name

    def verify(self) -> dict:
        prev = "0"*64
        for row in self.records():
            expected = digest([row["id"],row["kind"],row["recorded_at"],row["payload"],prev])
            if row["previous_hash"] != prev or row["record_hash"] != expected:
                raise ValueError(f"Ledger verification failed at sequence {row['seq']}")
            prev = row["record_hash"]
        check = self.db.execute("PRAGMA integrity_check").fetchone()[0]
        if check != "ok":
            raise ValueError(check)
        return {"records": len(self.records()), "head_hash":prev, "integrity":"ok"}
