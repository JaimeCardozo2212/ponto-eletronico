"""
Database module — SQLite schema, connection, and CRUD operations for:
- time_entries (daily punches)
- projects
- project_allocations (hours per project per day)
- holidays
- settings
"""

import sqlite3
import os
from datetime import date, datetime, time
from typing import Any

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "ponto.db")


def get_connection() -> sqlite3.Connection:
    """Return a connection with row_factory enabled."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all tables and default settings if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS time_entries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        DATE NOT NULL,
            start_time  TIME,
            lunch_start TIME,
            lunch_end   TIME,
            end_time    TIME,
            notes       TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS projects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            description TEXT,
            color       TEXT DEFAULT '#1f77b4',
            active      BOOLEAN DEFAULT 1,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS companies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            description TEXT,
            color       TEXT DEFAULT '#2ca02c',
            active      BOOLEAN DEFAULT 1,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS project_allocations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            time_entry_id   INTEGER NOT NULL,
            project_id      INTEGER NOT NULL,
            company_id      INTEGER,
            hours           REAL NOT NULL,
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (time_entry_id) REFERENCES time_entries(id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS holidays (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            date        DATE NOT NULL,
            recurring   BOOLEAN DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)

    # ── Migration: add company_id to project_allocations on existing DBs ──
    existing_cols = [
        row["name"] for row in cursor.execute("PRAGMA table_info(project_allocations)").fetchall()
    ]
    if "company_id" not in existing_cols:
        cursor.execute("ALTER TABLE project_allocations ADD COLUMN company_id INTEGER")

    # Default settings (only insert if not present)
    defaults = {
        "daily_hours": "8",
        "weekly_hours": "40",
        "ignore_weekends": "1",
        "reminder_entry": "08:00",
        "reminder_exit": "17:30",
        "reminders_enabled": "0",
    }
    for key, value in defaults.items():
        cursor.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )

    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# TIME ENTRIES CRUD
# ──────────────────────────────────────────────

def create_time_entry(
    entry_date: date,
    start_time: time | None = None,
    lunch_start: time | None = None,
    lunch_end: time | None = None,
    end_time: time | None = None,
    notes: str | None = None,
) -> int:
    """Insert a new time entry. Returns the new row id."""
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO time_entries (date, start_time, lunch_start, lunch_end, end_time, notes)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            entry_date.isoformat(),
            start_time.strftime("%H:%M") if start_time else None,
            lunch_start.strftime("%H:%M") if lunch_start else None,
            lunch_end.strftime("%H:%M") if lunch_end else None,
            end_time.strftime("%H:%M") if end_time else None,
            notes,
        ),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def update_time_entry(
    entry_id: int,
    entry_date: date,
    start_time: time | None = None,
    lunch_start: time | None = None,
    lunch_end: time | None = None,
    end_time: time | None = None,
    notes: str | None = None,
) -> None:
    """Update an existing time entry."""
    conn = get_connection()
    conn.execute(
        """UPDATE time_entries
           SET date = ?, start_time = ?, lunch_start = ?,
               lunch_end = ?, end_time = ?, notes = ?
           WHERE id = ?""",
        (
            entry_date.isoformat(),
            start_time.strftime("%H:%M") if start_time else None,
            lunch_start.strftime("%H:%M") if lunch_start else None,
            lunch_end.strftime("%H:%M") if lunch_end else None,
            end_time.strftime("%H:%M") if end_time else None,
            notes,
            entry_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_time_entry(entry_id: int) -> None:
    """Delete a time entry (cascades to project_allocations)."""
    conn = get_connection()
    conn.execute("DELETE FROM time_entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


def get_time_entry(entry_id: int) -> dict | None:
    """Return a single time entry as dict, or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM time_entries WHERE id = ?", (entry_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_time_entries(
    start_date: date | None = None,
    end_date: date | None = None,
    project_id: int | None = None,
    order_desc: bool = True,
) -> list[dict]:
    """Return time entries with optional date/project filters.
    When project_id is given, only entries that have allocations for that project.
    """
    conn = get_connection()
    query = "SELECT te.* FROM time_entries te"
    params: list[Any] = []

    if project_id is not None:
        query += """
            INNER JOIN project_allocations pa ON pa.time_entry_id = te.id
            WHERE pa.project_id = ?
        """
        params.append(project_id)
        if start_date:
            query += " AND te.date >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND te.date <= ?"
            params.append(end_date.isoformat())
    else:
        conditions = []
        if start_date:
            conditions.append("te.date >= ?")
            params.append(start_date.isoformat())
        if end_date:
            conditions.append("te.date <= ?")
            params.append(end_date.isoformat())
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY te.date " + ("DESC" if order_desc else "ASC")
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_time_entry_with_allocations(entry_id: int) -> dict:
    """Return a time entry dict with its project_allocations list attached."""
    entry = get_time_entry(entry_id)
    if entry is None:
        return {}
    conn = get_connection()
    allocs = conn.execute(
        """SELECT pa.*, p.name AS project_name, p.color AS project_color,
                  c.name AS company_name, c.color AS company_color
           FROM project_allocations pa
           JOIN projects p ON p.id = pa.project_id
           LEFT JOIN companies c ON c.id = pa.company_id
           WHERE pa.time_entry_id = ?""",
        (entry_id,),
    ).fetchall()
    conn.close()
    entry["allocations"] = [dict(a) for a in allocs]
    return entry


# ──────────────────────────────────────────────
# PROJECTS CRUD
# ──────────────────────────────────────────────

def create_project(name: str, description: str = "", color: str = "#1f77b4") -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO projects (name, description, color) VALUES (?, ?, ?)",
        (name, description, color),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def update_project(project_id: int, name: str, description: str = "", color: str = "#1f77b4") -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE projects SET name = ?, description = ?, color = ? WHERE id = ?",
        (name, description, color, project_id),
    )
    conn.commit()
    conn.close()


def toggle_project_active(project_id: int, active: bool) -> None:
    conn = get_connection()
    conn.execute("UPDATE projects SET active = ? WHERE id = ?", (int(active), project_id))
    conn.commit()
    conn.close()


def get_project(project_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_projects(active_only: bool = False) -> list[dict]:
    conn = get_connection()
    query = "SELECT * FROM projects"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY name"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_project_hours_total(project_id: int, start_date: date | None = None, end_date: date | None = None) -> float:
    """Return total hours allocated to a project in the given period."""
    conn = get_connection()
    query = "SELECT COALESCE(SUM(pa.hours), 0) FROM project_allocations pa"
    params: list[Any] = []
    conditions = ["pa.project_id = ?"]
    params.append(project_id)

    if start_date:
        query += " JOIN time_entries te ON te.id = pa.time_entry_id"
        conditions.append("te.date >= ?")
        params.append(start_date.isoformat())
        if end_date:
            conditions.append("te.date <= ?")
            params.append(end_date.isoformat())

    query += " WHERE " + " AND ".join(conditions)
    row = conn.execute(query, params).fetchone()
    conn.close()
    return float(row[0])


# ──────────────────────────────────────────────
# COMPANIES CRUD
# ──────────────────────────────────────────────

def create_company(name: str, description: str = "", color: str = "#2ca02c") -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO companies (name, description, color) VALUES (?, ?, ?)",
        (name, description, color),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def update_company(company_id: int, name: str, description: str = "", color: str = "#2ca02c") -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE companies SET name = ?, description = ?, color = ? WHERE id = ?",
        (name, description, color, company_id),
    )
    conn.commit()
    conn.close()


def toggle_company_active(company_id: int, active: bool) -> None:
    conn = get_connection()
    conn.execute("UPDATE companies SET active = ? WHERE id = ?", (int(active), company_id))
    conn.commit()
    conn.close()


def get_company(company_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_companies(active_only: bool = False) -> list[dict]:
    conn = get_connection()
    query = "SELECT * FROM companies"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY name"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_company_hours_total(company_id: int, start_date: date | None = None, end_date: date | None = None) -> float:
    """Return total hours allocated to a company in the given period."""
    conn = get_connection()
    query = "SELECT COALESCE(SUM(pa.hours), 0) FROM project_allocations pa"
    params: list[Any] = []
    conditions = ["pa.company_id = ?"]
    params.append(company_id)

    if start_date:
        query += " JOIN time_entries te ON te.id = pa.time_entry_id"
        conditions.append("te.date >= ?")
        params.append(start_date.isoformat())
        if end_date:
            conditions.append("te.date <= ?")
            params.append(end_date.isoformat())

    query += " WHERE " + " AND ".join(conditions)
    row = conn.execute(query, params).fetchone()
    conn.close()
    return float(row[0])


# ──────────────────────────────────────────────
# PROJECT ALLOCATIONS CRUD
# ──────────────────────────────────────────────

def create_allocation(
    time_entry_id: int,
    project_id: int,
    hours: float,
    notes: str = "",
    company_id: int | None = None,
) -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO project_allocations (time_entry_id, project_id, company_id, hours, notes) "
        "VALUES (?, ?, ?, ?, ?)",
        (time_entry_id, project_id, company_id, hours, notes),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def delete_allocation(allocation_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM project_allocations WHERE id = ?", (allocation_id,))
    conn.commit()
    conn.close()


def delete_allocations_for_entry(time_entry_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM project_allocations WHERE time_entry_id = ?", (time_entry_id,))
    conn.commit()
    conn.close()


def get_allocations_for_entry(time_entry_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT pa.*, p.name AS project_name, p.color AS project_color,
                  c.name AS company_name, c.color AS company_color
           FROM project_allocations pa
           JOIN projects p ON p.id = pa.project_id
           LEFT JOIN companies c ON c.id = pa.company_id
           WHERE pa.time_entry_id = ?""",
        (time_entry_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_allocations_summary(start_date: date | None = None, end_date: date | None = None) -> list[dict]:
    """Return hours grouped by project for a date range."""
    conn = get_connection()
    query = """
        SELECT p.id, p.name, p.color, COALESCE(SUM(pa.hours), 0) AS total_hours
        FROM project_allocations pa
        JOIN projects p ON p.id = pa.project_id
        JOIN time_entries te ON te.id = pa.time_entry_id
        WHERE 1=1
    """
    params: list[Any] = []
    if start_date:
        query += " AND te.date >= ?"
        params.append(start_date.isoformat())
    if end_date:
        query += " AND te.date <= ?"
        params.append(end_date.isoformat())
    query += " GROUP BY p.id ORDER BY total_hours DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_company_allocations_summary(start_date: date | None = None, end_date: date | None = None) -> list[dict]:
    """Return hours grouped by company for a date range."""
    conn = get_connection()
    query = """
        SELECT c.id, c.name, c.color, COALESCE(SUM(pa.hours), 0) AS total_hours
        FROM project_allocations pa
        JOIN companies c ON c.id = pa.company_id
        JOIN time_entries te ON te.id = pa.time_entry_id
        WHERE 1=1
    """
    params: list[Any] = []
    if start_date:
        query += " AND te.date >= ?"
        params.append(start_date.isoformat())
    if end_date:
        query += " AND te.date <= ?"
        params.append(end_date.isoformat())
    query += " GROUP BY c.id ORDER BY total_hours DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_allocations_detailed(
    start_date: date | None = None,
    end_date: date | None = None,
    company_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> list[dict]:
    """Return individual allocations enriched with the entry date and the
    project/company names, optionally filtered by date range, companies and
    projects. An empty/None list for company_ids/project_ids means "no filter".
    Powers the Dashboard filters (multi-select by company and project).
    """
    conn = get_connection()
    query = """
        SELECT pa.id, pa.hours, pa.project_id, pa.company_id,
               te.date AS entry_date,
               p.name AS project_name, p.color AS project_color,
               c.name AS company_name, c.color AS company_color
        FROM project_allocations pa
        JOIN time_entries te ON te.id = pa.time_entry_id
        JOIN projects p ON p.id = pa.project_id
        LEFT JOIN companies c ON c.id = pa.company_id
        WHERE 1=1
    """
    params: list[Any] = []
    if start_date:
        query += " AND te.date >= ?"
        params.append(start_date.isoformat())
    if end_date:
        query += " AND te.date <= ?"
        params.append(end_date.isoformat())
    if company_ids:
        placeholders = ", ".join("?" for _ in company_ids)
        query += f" AND pa.company_id IN ({placeholders})"
        params.extend(company_ids)
    if project_ids:
        placeholders = ", ".join("?" for _ in project_ids)
        query += f" AND pa.project_id IN ({placeholders})"
        params.extend(project_ids)
    query += " ORDER BY te.date"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────
# HOLIDAYS CRUD
# ──────────────────────────────────────────────

def create_holiday(name: str, holiday_date: date, recurring: bool = False) -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO holidays (name, date, recurring) VALUES (?, ?, ?)",
        (name, holiday_date.isoformat(), int(recurring)),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def delete_holiday(holiday_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM holidays WHERE id = ?", (holiday_id,))
    conn.commit()
    conn.close()


def get_holidays() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM holidays ORDER BY date").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_holiday(check_date: date) -> bool:
    """Check if a date is a holiday (supports recurring yearly holidays)."""
    conn = get_connection()
    # Match exact date OR recurring same day/month
    rows = conn.execute(
        """SELECT id FROM holidays
           WHERE date = ? OR (recurring = 1 AND strftime('%m-%d', date) = ?)""",
        (check_date.isoformat(), check_date.strftime("%m-%d")),
    ).fetchall()
    conn.close()
    return len(rows) > 0


# ──────────────────────────────────────────────
# SETTINGS
# ──────────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, value),
    )
    conn.commit()
    conn.close()


def get_all_settings() -> dict[str, str]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}
