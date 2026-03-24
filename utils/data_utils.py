"""
CitiZen AI — Complete Database Layer
SQLite database with all CRUD operations for complaints, users, agents, and ML tracking.
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "complaints.db")


def get_connection():
    """Get a database connection with WAL mode for concurrent reads."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    """Create all tables and indexes if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        identity_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        status TEXT DEFAULT 'active'
    );

    CREATE TABLE IF NOT EXISTS agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        agent_id TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        department TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        total_resolved INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active'
    );

    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        address TEXT,
        landmark TEXT,
        image_path TEXT,
        image_hash TEXT,
        lat REAL,
        lon REAL,
        ai_urgency TEXT DEFAULT 'Medium',
        user_urgency TEXT DEFAULT 'Medium',
        ai_confidence REAL DEFAULT 0.0,
        ai_method TEXT DEFAULT 'text',
        status TEXT DEFAULT 'Pending',
        assigned_agent TEXT,
        department TEXT,
        resolution_notes TEXT,
        estimated_resolution TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP,
        is_duplicate INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS complaint_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER NOT NULL,
        old_status TEXT,
        new_status TEXT NOT NULL,
        changed_by TEXT,
        change_reason TEXT,
        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (complaint_id) REFERENCES complaints(id)
    );

    CREATE TABLE IF NOT EXISTS corrections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER NOT NULL,
        original_prediction TEXT,
        corrected_label TEXT,
        original_urgency TEXT,
        corrected_urgency TEXT,
        corrected_by TEXT,
        corrected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        image_path TEXT,
        description TEXT,
        category TEXT,
        FOREIGN KEY (complaint_id) REFERENCES complaints(id)
    );

    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (complaint_id) REFERENCES complaints(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS model_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        version_num INTEGER NOT NULL,
        trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_samples INTEGER DEFAULT 0,
        real_samples INTEGER DEFAULT 0,
        accuracy REAL DEFAULT 0.0,
        correction_samples INTEGER DEFAULT 0,
        notes TEXT
    );
    
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        user_type TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL
    );

    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        department TEXT,
        status TEXT DEFAULT 'Open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_read_admin INTEGER DEFAULT 0,
        is_read_worker INTEGER DEFAULT 0
    );
    """)

    # Create indexes
    index_statements = [
        "CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status)",
        "CREATE INDEX IF NOT EXISTS idx_complaints_urgency ON complaints(ai_urgency)",
        "CREATE INDEX IF NOT EXISTS idx_complaints_category ON complaints(category)",
        "CREATE INDEX IF NOT EXISTS idx_complaints_created ON complaints(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_complaints_user ON complaints(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_complaints_agent ON complaints(assigned_agent)",
        "CREATE INDEX IF NOT EXISTS idx_complaints_hash ON complaints(image_hash)",
        "CREATE INDEX IF NOT EXISTS idx_agents_dept ON agents(department)"
    ]
    for statement in index_statements:
        try:
            cursor.execute(statement)
        except Exception:
            pass

    # Migration: Add department column to complaints if it doesn't exist
    try:
        cursor.execute("SELECT department FROM complaints LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor.execute("ALTER TABLE complaints ADD COLUMN department TEXT")
        except Exception:
            pass

    # Migration: Add city and pincode to users table IF NOT EXISTS
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN city TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN pincode TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN identity_id TEXT")
    except Exception:
        pass

    conn.commit()
    conn.close()


# ─── USER OPERATIONS ──────────────────────────────────────────────────

def add_user(name, email, password_hash, city=None, pincode=None, identity_id=None):
    """Register a new citizen."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, city, pincode, identity_id) VALUES (?, ?, ?, ?, ?, ?)",
            (name, email, password_hash, city, pincode, identity_id)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        return None
    except Exception:
        return None


def authenticate_user(email, password_hash):
    """Authenticate a citizen by email and password hash."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email = ? AND password_hash = ?",
            (email, password_hash)
        )
        user = cursor.fetchone()
        if user:
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now().isoformat(), user["id"])
            )
            conn.commit()
        conn.close()
        return dict(user) if user else None
    except Exception:
        return None


# ─── AGENT OPERATIONS ─────────────────────────────────────────────────

def add_agent(name, agent_id, password_hash, department):
    """Register a new agent."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO agents (name, agent_id, password_hash, department) VALUES (?, ?, ?, ?)",
            (name, agent_id, password_hash, department)
        )
        conn.commit()
        aid = cursor.lastrowid
        conn.close()
        return aid
    except sqlite3.IntegrityError:
        return None
    except Exception:
        return None


def authenticate_agent(agent_id, password_hash):
    """Authenticate an agent by agent_id and password hash."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM agents WHERE agent_id = ? AND password_hash = ?",
            (agent_id, password_hash)
        )
        agent = cursor.fetchone()
        if agent:
            cursor.execute(
                "UPDATE agents SET last_login = ? WHERE id = ?",
                (datetime.now().isoformat(), agent["id"])
            )
            conn.commit()
        conn.close()
        return dict(agent) if agent else None
    except Exception:
        return None


# ─── COMPLAINT OPERATIONS ─────────────────────────────────────────────

def add_complaint(user_id, category, description, address, landmark,
                  image_path, image_hash, lat, lon, ai_urgency,
                  user_urgency, ai_confidence, ai_method,
                  estimated_resolution="", department="General"):
    """Insert a new complaint and return its ID."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO complaints
            (user_id, category, description, address, landmark,
             image_path, image_hash, lat, lon, ai_urgency,
             user_urgency, ai_confidence, ai_method,
             estimated_resolution, department, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, category, description, address, landmark,
              image_path, image_hash, lat, lon, ai_urgency,
              user_urgency, ai_confidence, ai_method,
              estimated_resolution, department, now, now))
        complaint_id = cursor.lastrowid

        # Record initial status
        cursor.execute("""
            INSERT INTO complaint_history
            (complaint_id, old_status, new_status, changed_by, change_reason, changed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (complaint_id, None, "Pending", f"user_{user_id}", "Complaint submitted", now))

        conn.commit()
        conn.close()
        return complaint_id
    except Exception as e:
        print(f"Error adding complaint: {e}")
        return None


def get_all_complaints():
    """Get all complaints ordered by urgency priority."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM complaints
            ORDER BY
                CASE ai_urgency
                    WHEN 'High' THEN 1
                    WHEN 'Medium' THEN 2
                    WHEN 'Low' THEN 3
                    ELSE 4
                END,
                created_at DESC
        """)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


def get_user_complaints(user_id):
    """Get all complaints for a specific user."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM complaints WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


def get_complaint_by_id(complaint_id):
    """Get a single complaint with its full history."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,))
        complaint = cursor.fetchone()
        if not complaint:
            conn.close()
            return None
        result = dict(complaint)

        cursor.execute(
            "SELECT * FROM complaint_history WHERE complaint_id = ? ORDER BY changed_at ASC",
            (complaint_id,)
        )
        result["history"] = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return result
    except Exception:
        return None


def update_complaint_status(complaint_id, new_status, agent_id=None, notes=None):
    """Update a complaint's status and log the change."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("SELECT status FROM complaints WHERE id = ?", (complaint_id,))
        row = cursor.fetchone()
        old_status = row["status"] if row else "Unknown"

        update_fields = "status = ?, updated_at = ?"
        update_values = [new_status, now]

        if agent_id:
            update_fields += ", assigned_agent = ?"
            update_values.append(agent_id)
        if notes:
            update_fields += ", resolution_notes = ?"
            update_values.append(notes)
        if new_status == "Resolved":
            update_fields += ", resolved_at = ?"
            update_values.append(now)

        update_values.append(complaint_id)
        cursor.execute(f"UPDATE complaints SET {update_fields} WHERE id = ?", update_values)

        cursor.execute("""
            INSERT INTO complaint_history
            (complaint_id, old_status, new_status, changed_by, change_reason, changed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (complaint_id, old_status, new_status, agent_id or "system", notes or "", now))

        # Increment agent's resolved count
        if new_status == "Resolved" and agent_id:
            cursor.execute(
                "UPDATE agents SET total_resolved = total_resolved + 1 WHERE agent_id = ?",
                (agent_id,)
            )

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating complaint status: {e}")
        return False


def search_complaints(term=None, status_filter=None, urgency_filter=None,
                      category_filter=None, department_filter=None):
    """Search and filter complaints."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM complaints WHERE 1=1"
        params = []

        if term:
            query += " AND (description LIKE ? OR address LIKE ? OR category LIKE ?)"
            params.extend([f"%{term}%"] * 3)
        if status_filter and status_filter != "All":
            query += " AND status = ?"
            params.append(status_filter)
        if urgency_filter and urgency_filter != "All":
            query += " AND ai_urgency = ?"
            params.append(urgency_filter)
        if category_filter and category_filter != "All":
            query += " AND category = ?"
            params.append(category_filter)
        if department_filter:
            query += " AND LOWER(TRIM(department)) = LOWER(TRIM(?))"
            params.append(department_filter)

        query += """
            ORDER BY
                CASE ai_urgency WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 ELSE 4 END,
                created_at DESC
        """
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


# ─── CORRECTION OPERATIONS ─────────────────────────────────────────────

def add_correction(complaint_id, original_prediction, corrected_label,
                   original_urgency, corrected_urgency, corrected_by,
                   image_path=None, description=None, category=None):
    """Record an AI correction from an agent."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO corrections
            (complaint_id, original_prediction, corrected_label,
             original_urgency, corrected_urgency, corrected_by,
             image_path, description, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (complaint_id, original_prediction, corrected_label,
              original_urgency, corrected_urgency, corrected_by,
              image_path, description, category))

        # Also update the complaint's category/urgency
        updates = []
        params = []
        if corrected_label and corrected_label != original_prediction:
            updates.append("category = ?")
            params.append(corrected_label)
        if corrected_urgency and corrected_urgency != original_urgency:
            updates.append("ai_urgency = ?")
            params.append(corrected_urgency)
        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(complaint_id)
            cursor.execute(f"UPDATE complaints SET {', '.join(updates)} WHERE id = ?", params)

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding correction: {e}")
        return False


def get_correction_count_since_last_training():
    """Count corrections since the last model training."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(trained_at) as last_trained FROM model_versions"
        )
        row = cursor.fetchone()
        last_trained = row["last_trained"] if row and row["last_trained"] else "2000-01-01"

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM corrections WHERE corrected_at > ?",
            (last_trained,)
        )
        count = cursor.fetchone()["cnt"]
        conn.close()
        return count
    except Exception:
        return 0


def get_all_corrections():
    """Get all corrections."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM corrections ORDER BY corrected_at DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


# ─── FEEDBACK OPERATIONS ──────────────────────────────────────────────

def add_feedback(complaint_id, user_id, rating, comment=""):
    """Add user feedback for a resolved complaint."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO feedback (complaint_id, user_id, rating, comment) VALUES (?, ?, ?, ?)",
            (complaint_id, user_id, rating, comment)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ─── MODEL VERSION OPERATIONS ─────────────────────────────────────────

def get_model_versions():
    """Get all model version records."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM model_versions ORDER BY version_num ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


def save_model_version(version_num, total_samples, real_samples, accuracy,
                       correction_samples=0, notes=""):
    """Save a new model version record."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO model_versions
            (version_num, total_samples, real_samples, accuracy, correction_samples, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (version_num, total_samples, real_samples, accuracy,
              correction_samples, notes))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ─── STATISTICS & ANALYTICS ───────────────────────────────────────────

def get_complaint_stats():
    """Get aggregated complaint statistics."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        stats = {}

        cursor.execute("SELECT COUNT(*) as total FROM complaints")
        stats["total"] = cursor.fetchone()["total"]

        for status in ["Pending", "In Progress", "Resolved"]:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM complaints WHERE status = ?", (status,)
            )
            stats[status.lower().replace(" ", "_")] = cursor.fetchone()["cnt"]

        for urgency in ["High", "Medium", "Low"]:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM complaints WHERE ai_urgency = ?", (urgency,)
            )
            stats[f"urgency_{urgency.lower()}"] = cursor.fetchone()["cnt"]

        # Average resolution time in hours
        cursor.execute("""
            SELECT AVG(
                (julianday(resolved_at) - julianday(created_at)) * 24
            ) as avg_hours
            FROM complaints WHERE resolved_at IS NOT NULL
        """)
        row = cursor.fetchone()
        stats["avg_resolution_hours"] = round(row["avg_hours"], 1) if row["avg_hours"] else 0

        # Today's resolved
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM complaints WHERE status='Resolved' AND date(resolved_at) = date('now')"
        )
        stats["resolved_today"] = cursor.fetchone()["cnt"]

        # Category breakdown
        cursor.execute(
            "SELECT category, COUNT(*) as count FROM complaints GROUP BY category ORDER BY count DESC"
        )
        stats["by_category"] = [dict(r) for r in cursor.fetchall()]

        conn.close()
        return stats
    except Exception:
        return {
            "total": 0, "pending": 0, "in_progress": 0, "resolved": 0,
            "urgency_high": 0, "urgency_medium": 0, "urgency_low": 0,
            "avg_resolution_hours": 0, "resolved_today": 0, "by_category": []
        }


def get_dashboard_summary():
    """Get a summary for dashboard display."""
    return get_complaint_stats()


def check_duplicate(image_hash, lat=None, lon=None, category=None):
    """Check if a complaint is a duplicate based on image hash and proximity."""
    if not image_hash:
        return False
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, lat, lon FROM complaints WHERE image_hash = ? AND status != 'Resolved'",
            (image_hash,)
        )
        matches = cursor.fetchall()
        conn.close()
        if matches:
            return True
        return False
    except Exception:
        return False


def export_complaints_csv(status_filter=None, category_filter=None,
                          urgency_filter=None):
    """Export complaints to a pandas DataFrame."""
    import pandas as pd
    try:
        complaints = search_complaints(
            status_filter=status_filter,
            urgency_filter=urgency_filter,
            category_filter=category_filter
        )
        if not complaints:
            return pd.DataFrame()
        df = pd.DataFrame(complaints)
        cols_to_keep = [
            "id", "category", "description", "address", "ai_urgency",
            "user_urgency", "ai_confidence", "status", "assigned_agent",
            "resolution_notes", "created_at", "resolved_at"
        ]
        available_cols = [c for c in cols_to_keep if c in df.columns]
        return df[available_cols]
    except Exception:
        import pandas as pd
        return pd.DataFrame()


def get_complaints_with_coords():
    """Get all complaints that have lat/lon coordinates for mapping."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM complaints
            WHERE lat IS NOT NULL AND lon IS NOT NULL
            ORDER BY
                CASE ai_urgency WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 ELSE 4 END,
                created_at DESC
        """)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


def get_agent_leaderboard():
    """Get agent leaderboard sorted by resolved count."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, agent_id, department, total_resolved FROM agents ORDER BY total_resolved DESC"
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


def get_daily_trend(days=30):
    """Get daily complaint count for trend chart."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT date(created_at) as day, COUNT(*) as count
            FROM complaints
            WHERE created_at >= datetime('now', '-{days} days')
            GROUP BY date(created_at)
            ORDER BY day ASC
        """)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


# ─── SESSION OPERATIONS ───────────────────────────────────────────────

import secrets

def create_session(user_id, user_type, duration_minutes=10):
    """Create a persistent session and return the ID."""
    try:
        session_id = secrets.token_urlsafe(32)
        conn = get_connection()
        cursor = conn.cursor()
        expires_at = (datetime.now().timestamp() + (duration_minutes * 60))
        cursor.execute(
            "INSERT INTO sessions (session_id, user_id, user_type, expires_at) VALUES (?, ?, ?, ?)",
            (session_id, user_id, user_type, expires_at)
        )
        conn.commit()
        conn.close()
        return session_id
    except Exception as e:
        print(f"Error creating session: {e}")
        return None

def get_active_session(session_id):
    """Retrieve an active session if not expired."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        
        cursor.execute("SELECT * FROM sessions WHERE session_id = ? AND expires_at > ?", (session_id, now))
        session = cursor.fetchone()
        
        if not session:
            conn.close()
            return None
            
        if session["user_type"] == "citizen":
            cursor.execute("SELECT id, name, email FROM users WHERE id = ?", (session["user_id"],))
        else:
            cursor.execute("SELECT id, name, agent_id, department FROM agents WHERE id = ?", (session["user_id"],))
            
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return {
                "session_info": dict(session),
                "user_data": dict(user_data)
            }
        return None
    except Exception as e:
        print(f"Error getting session: {e}")
        return None

def delete_session(session_id):
    """Remove a session from the database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def cleanup_sessions():
    """Remove expired sessions."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        cursor.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
        conn.commit()
        conn.close()
    except Exception:
        pass


# ─── TICKET OPERATIONS ────────────────────────────────────────────────

def add_ticket(complaint_id, user_id, message, department):
    """Raise a new support ticket for a complaint."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO tickets (complaint_id, user_id, message, department, status)
               VALUES (?, ?, ?, ?, 'Open')""",
            (complaint_id, user_id, message, department)
        )
        conn.commit()
        ticket_id = cursor.lastrowid
        conn.close()
        return ticket_id
    except Exception as e:
        print(f"Error adding ticket: {e}")
        return None


def get_tickets_for_admin():
    """Return all tickets (for admin inbox)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM tickets ORDER BY created_at DESC"
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


def get_tickets_by_department(dept):
    """Return tickets filtered by department (for worker inbox)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM tickets WHERE TRIM(LOWER(department)) = TRIM(LOWER(?)) ORDER BY created_at DESC",
            (dept,)
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


def mark_tickets_read_admin():
    """Mark all tickets as read by admin."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE tickets SET is_read_admin = 1")
        conn.commit()
        conn.close()
    except Exception:
        pass


def mark_tickets_read_worker(dept):
    """Mark all tickets in a department as read by worker."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tickets SET is_read_worker = 1 WHERE TRIM(LOWER(department)) = TRIM(LOWER(?))",
            (dept,)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_unread_count_admin():
    """Return count of tickets not yet read by admin."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE is_read_admin = 0")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def get_unread_count_worker(dept):
    """Return count of unread tickets for a worker's department."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM tickets WHERE is_read_worker = 0 AND TRIM(LOWER(department)) = TRIM(LOWER(?))",
            (dept,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0
