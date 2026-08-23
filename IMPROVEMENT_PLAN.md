# TrackItBoardIt — Improvement Plan

Analysis of [Track_it.py](Track_it.py) as it stands today, and a proposed restructure.

## Current problems

**Correctness**
- `User.create_account()` never calls `connection.commit()` (it's commented out at [Track_it.py:64](Track_it.py#L64)). With MySQL's default `autocommit=False`, new accounts are inserted into the transaction but never persisted — they vanish on disconnect.
- `n=int(Prompt.ask(...))` at [Track_it.py:237](Track_it.py#L237) crashes with an uncaught `ValueError` if the user types anything non-numeric.
- `Driver.remainig_seats` is stored as whatever string `Prompt.ask` returns ([Track_it.py:117](Track_it.py#L117)), never cast to `int`, while `filter_buses` later compares it with `== 0` ([Track_it.py:173](Track_it.py#L173)) — relies entirely on MySQL's implicit column cast to work.
- `filter_buses` mixes `print()` (plain stdout) with the rest of the app's `console.print()` (rich) — output styling is inconsistent ([Track_it.py:178-189](Track_it.py#L178-L189)).
- No `try/except` anywhere: any MySQL error (bad connection, constraint violation, network blip) crashes the whole app.
- The DB connection is opened once at import time ([Track_it.py:15-22](Track_it.py#L15-L22)) with no reconnect logic — a dropped connection kills the session permanently.

**Security**
- DB credentials are hardcoded in source (`host="localhost", user="root", password="root"`) — not viable once this leaves your machine, and normalizes committing secrets.
- Passwords (`pin`) are stored and compared in plaintext, with no hashing.
- No password-confirmation step on account creation.

**Architecture**
- Everything — DB connection, schema-shaped SQL, business logic (distance/ETA calculation), and terminal UI (`rich` prompts and tables) — lives in one 265-line file with no boundaries between them.
- `User`, `Driver`, and `Passenger` classes each both *collect input* and *persist to the DB*, so none of the logic is testable without a live MySQL instance and a terminal.
- A single global `cursor` is shared and mutated across every class — nothing is dependency-injected, so nothing can be swapped out or mocked in a test.
- No config file, no `requirements.txt`, no schema file (the DB schema is only inferable by reading the SQL strings), no tests.

## Proposed structure

Small project, so keep it flat — a `src/` package with a clear layer split, not a deep tree.

```
trackitboardit/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── sql/
│   └── schema.sql              # CREATE TABLE statements (currently undocumented)
├── src/
│   └── trackitboardit/
│       ├── __init__.py
│       ├── main.py             # entry point: the menu loop only
│       ├── config.py           # reads DB_HOST/DB_USER/DB_PASSWORD/DB_NAME from env
│       ├── db.py               # connection factory (context manager, reconnect-safe)
│       ├── models.py           # Bus, Passenger, Driver as plain dataclasses (no I/O)
│       ├── repositories.py     # all raw SQL, one function per query
│       ├── services.py         # auth (hashing) + matching (distance/ETA/filter) logic
│       └── cli.py              # all rich Prompt/Console/Table code
└── tests/
    ├── test_services_matching.py   # haversine + filter_buses, pure functions, no DB
    └── test_services_auth.py       # hashing/verification logic
```

**Layer rules:**
- `repositories.py` is the only file allowed to import `mysql.connector` or write SQL.
- `services.py` contains business logic (haversine distance, ETA, route filtering, password hashing) as plain functions — no `rich`, no `input()`, no SQL. This is what unit tests target.
- `cli.py` is the only file allowed to import `rich` or call `Prompt.ask`/`input`. It calls into `services` and `repositories`.
- `main.py` just wires the menu loop, ~20 lines.

## Minimal code sketch

`config.py` — no more hardcoded credentials:

```python
import os

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ["DB_PASSWORD"],
    "database": os.environ.get("DB_NAME", "trackitboardit"),
}
```

`db.py` — connection as a context manager, not a module-level global:

```python
from contextlib import contextmanager
import mysql.connector
from .config import DB_CONFIG

@contextmanager
def get_cursor():
    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        cur = conn.cursor(dictionary=True)
        yield cur
        conn.commit()
    finally:
        conn.close()
```

`repositories.py` — one function per query, always uses `get_cursor()`:

```python
from .db import get_cursor

def find_user(role: str, username: str) -> dict | None:
    table = "drivers" if role == "driver" else "passengers"
    with get_cursor() as cur:
        cur.execute(f"SELECT * FROM {table} WHERE username=%s", (username,))
        return cur.fetchone()

def create_user(role: str, username: str, password_hash: str) -> bool:
    table = "drivers" if role == "driver" else "passengers"
    if find_user(role, username):
        return False
    with get_cursor() as cur:
        cur.execute(f"INSERT INTO {table} (username, pin) VALUES (%s, %s)", (username, password_hash))
    return True
```

(`table` is chosen from a fixed `{"driver", "passenger"}` set validated by the caller before it reaches here — never from raw user input — so this stays injection-safe despite the f-string.)

`services.py` — pure logic, hashing instead of plaintext, unit-testable with no DB or terminal:

```python
import math
from passlib.hash import bcrypt

def hash_password(raw: str) -> str:
    return bcrypt.hash(raw)

def verify_password(raw: str, hashed: str) -> bool:
    return bcrypt.verify(raw, hashed)

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    d_lat, d_lon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))
```

`main.py` — the whole entry point:

```python
from .cli import run_menu

def main():
    run_menu()

if __name__ == "__main__":
    main()
```

## Migration order

1. Add `.env` + `config.py`, stop hardcoding credentials — smallest change, removes the biggest security smell.
2. Extract `repositories.py` from the existing SQL calls; fix the missing `commit()` bug while doing it.
3. Extract `services.py` (haversine + `filter_buses` + hashing); write the two test files against it — this is the first code in the project that's testable without MySQL running.
4. Extract `cli.py`, replace `int(Prompt.ask(...))` with `rich.prompt.IntPrompt.ask(...)` to fix the crash-on-bad-input bug.
5. Shrink `Track_it.py` down to `main.py` and delete it.
6. Write `sql/schema.sql` from the live DB (`mysqldump --no-data trackitboardit`) so the schema is no longer only inferable from SQL strings scattered across the code.
