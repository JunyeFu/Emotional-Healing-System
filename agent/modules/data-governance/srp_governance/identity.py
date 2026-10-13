from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3
import uuid

from .errors import GovernanceError


_OPAQUE_REFERENCE = re.compile(r"^REC-[A-Z0-9_-]{8,64}$")
_ACTOR_ID = re.compile(r"^[a-z][a-z0-9-]{2,31}$")


class IdentityMappingStore:
    def __init__(self, *, database_path: Path, allowed_actors: set[str] | frozenset[str]) -> None:
        self.database_path = Path(database_path)
        self.allowed_actors = frozenset(allowed_actors)

    def _authorize(self, actor_id: str) -> None:
        if (
            not isinstance(actor_id, str)
            or not _ACTOR_ID.fullmatch(actor_id)
            or actor_id not in self.allowed_actors
        ):
            raise GovernanceError("UNAUTHORIZED")

    def create_or_get(self, opaque_reference: str, actor_id: str) -> str:
        self._authorize(actor_id)
        if not isinstance(opaque_reference, str) or not _OPAQUE_REFERENCE.fullmatch(opaque_reference):
            raise GovernanceError("INVALID_OPAQUE_REFERENCE")

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with closing(sqlite3.connect(self.database_path)) as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS research_mappings (
                        opaque_reference TEXT PRIMARY KEY,
                        research_id TEXT NOT NULL UNIQUE,
                        status TEXT NOT NULL CHECK(status IN ('ACTIVE','RETIRED')),
                        created_at_utc TEXT NOT NULL
                    )
                    """
                )
                existing = connection.execute(
                    "SELECT research_id FROM research_mappings WHERE opaque_reference = ?",
                    (opaque_reference,),
                ).fetchone()
                if existing is not None:
                    connection.commit()
                    return existing[0]
                research_id = f"SRP-R-{uuid.uuid4().hex}"
                connection.execute(
                    """
                    INSERT INTO research_mappings(
                        opaque_reference, research_id, status, created_at_utc
                    ) VALUES (?, ?, 'ACTIVE', ?)
                    """,
                    (
                        opaque_reference,
                        research_id,
                        datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
                    ),
                )
                connection.commit()
                return research_id
        except sqlite3.Error as exc:
            raise GovernanceError("IDENTITY_STORE_UNAVAILABLE") from exc
