# ClickUp Date Formatting

## Unix Epoch Timestamps

ClickUp API uses Unix time in **milliseconds** for all date fields:
- `due_date`, `start_date`, `date_created`, `date_updated`, `date_closed`, `date_done`

## ISO 8601 to Milliseconds

```
YYYY-MM-DD → Unix ms

Example: 2026-02-01 → 1738368000000
```

**Python helper** (`scripts/client.py`):
```python
from client import iso_to_milliseconds

ms = iso_to_milliseconds("2026-02-01")
# 1738368000000
```

## Milliseconds to ISO 8601

```
Unix ms → YYYY-MM-DD

Example: 1738368000000 → 2026-02-01
```

**Python helper** (`scripts/client.py`):
```python
from client import milliseconds_to_iso

date = milliseconds_to_iso(1738368000000)
# "2026-02-01"

# With time
from client import milliseconds_to_iso_full

datetime = milliseconds_to_iso_full(1738368000000)
# "2026-02-01 00:00:00"
```

## Time Zones

All ClickUp timestamps are UTC. Convert to local timezone as needed.

## Date-Time Flag

When `due_date_time` or `start_date_time` is `true`, the timestamp includes time of day.
When `false`, only the date part is considered.

**Create task with due date only (no time):**
```json
{
  "name": "Task",
  "due_date": 1738368000000,
  "due_date_time": false
}
```

**Create task with due date and time:**
```json
{
  "name": "Task",
  "due_date": 1738368000000,
  "due_date_time": true
}
```
