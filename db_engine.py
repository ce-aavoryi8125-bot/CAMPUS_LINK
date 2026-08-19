import os
import sqlite3
import re
from contextlib import contextmanager

try:
    import pymysql
    import pymysql.cursors
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False

def _load_env_or_registry(var_name, default=""):
    val = os.environ.get(var_name)
    if val:
        return val
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                reg_val, _ = winreg.QueryValueEx(key, var_name)
                return str(reg_val)
        except Exception:
            pass
    return default

import sys
# Environment Configuration
MYSQL_HOST = _load_env_or_registry("MYSQL_HOST", "localhost")
MYSQL_PORT = int(_load_env_or_registry("MYSQL_PORT", "3306"))
MYSQL_USER = _load_env_or_registry("MYSQL_USER", "root")
MYSQL_PASSWORD = _load_env_or_registry("MYSQL_PASSWORD", "")
MYSQL_DB = _load_env_or_registry("MYSQL_DB", "campuslink_umat")
USE_MYSQL = _load_env_or_registry("USE_MYSQL", "false").lower() in ("true", "1", "yes")

# SQLite Fallback Path
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "campuslink_umat.db")

_mysql_warning_shown = False
_mysql_available = False

def set_mysql_credentials(host=None, port=None, user=None, password=None, database=None, use_mysql=True):
    """
    Updates MySQL credentials dynamically at runtime.
    """
    global MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, USE_MYSQL, _mysql_warning_shown, _mysql_available
    if host is not None: MYSQL_HOST = host
    if port is not None: MYSQL_PORT = int(port)
    if user is not None: MYSQL_USER = user
    if password is not None: MYSQL_PASSWORD = password
    if database is not None: MYSQL_DB = database
    USE_MYSQL = use_mysql
    _mysql_warning_shown = False
    _mysql_available = False

def is_mysql_active():
    """
    Returns True if MySQL is currently connected and active.
    """
    global _mysql_available
    return _mysql_available

def get_connection(autocommit=True):
    """
    Returns an active database connection as a tuple (db_type, connection).
    Attempts MySQL first if configured; falls back reliably to SQLite.
    """
    global _mysql_warning_shown, _mysql_available
    if USE_MYSQL and HAS_PYMYSQL:
        try:
            conn = pymysql.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=autocommit
            )
            _mysql_available = True
            return ("mysql", conn)
        except Exception as e:
            try:
                # Attempt to create database if it doesn't exist
                conn_raw = pymysql.connect(
                    host=MYSQL_HOST,
                    port=MYSQL_PORT,
                    user=MYSQL_USER,
                    password=MYSQL_PASSWORD,
                    charset='utf8mb4',
                    autocommit=True
                )
                with conn_raw.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                conn_raw.close()
                
                conn = pymysql.connect(
                    host=MYSQL_HOST,
                    port=MYSQL_PORT,
                    user=MYSQL_USER,
                    password=MYSQL_PASSWORD,
                    database=MYSQL_DB,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=autocommit
                )
                _mysql_available = True
                return ("mysql", conn)
            except Exception as inner_e:
                _mysql_available = False
                if not _mysql_warning_shown:
                    print(f"[DB ENGINE INFO] MySQL unavailable ({inner_e}). Operating on SQLite engine.")
                    _mysql_warning_shown = True

    # SQLite Fallback Engine
    _mysql_available = False
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH, timeout=30.0, isolation_level=None if autocommit else "DEFERRED")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return ("sqlite", conn)

def normalize_query_for_engine(query, db_type):
    """
    Normalizes SQL syntax between SQLite and MySQL dialects.
    - Placeholder adaptation: '?' for SQLite, '%s' for MySQL.
    - INSERT OR IGNORE (SQLite) -> INSERT IGNORE (MySQL).
    - Backtick handling for reserved keywords.
    """
    clean_query = query.strip()
    if db_type == "mysql":
        # Convert SQLite 'INSERT OR IGNORE' to MySQL 'INSERT IGNORE'
        clean_query = re.sub(r'\bINSERT\s+OR\s+IGNORE\b', 'INSERT IGNORE', clean_query, flags=re.IGNORECASE)
        # Convert ? placeholders to %s
        clean_query = clean_query.replace("?", "%s")
    else:
        # SQLite: Convert MySQL 'INSERT IGNORE' to SQLite 'INSERT OR IGNORE'
        if re.search(r'\bINSERT\s+IGNORE\b', clean_query, flags=re.IGNORECASE) and not re.search(r'\bINSERT\s+OR\s+IGNORE\b', clean_query, flags=re.IGNORECASE):
            clean_query = re.sub(r'\bINSERT\s+IGNORE\b', 'INSERT OR IGNORE', clean_query, flags=re.IGNORECASE)
        # Remove MySQL-specific backticks on `condition` keyword for clean SQLite compatibility
        clean_query = clean_query.replace("`condition`", "condition")
    return clean_query

class TransactionContext:
    """
    Context wrapper for executing multiple SQL statements inside a single atomic transaction.
    Supports both SQLite and MySQL engines.
    """
    def __init__(self, db_type, conn):
        self.db_type = db_type
        self.conn = conn
        self.cursor = conn.cursor()

    def execute(self, query, params=None, fetch=None, fetchone=False):
        if params is None:
            params = ()
        if fetchone:
            fetch = "one"

        normalized = normalize_query_for_engine(query, self.db_type)
        q_upper = normalized.strip().upper()

        if fetch is None or fetch == "all":
            if q_upper.startswith("INSERT"):
                fetch = "lastrowid"
            elif q_upper.startswith("UPDATE") or q_upper.startswith("DELETE"):
                fetch = "rowcount"

        self.cursor.execute(normalized, params)

        if fetch == "all":
            rows = self.cursor.fetchall()
            if self.db_type == "mysql":
                return [dict(r) for r in rows]
            return [dict(r) for r in rows]
        elif fetch == "one":
            row = self.cursor.fetchone()
            if not row:
                return None
            return dict(row)
        elif fetch == "lastrowid":
            return self.cursor.lastrowid
        else:
            return self.cursor.rowcount

    def commit(self):
        self.conn.commit()

    def rollback(self):
        try:
            self.conn.rollback()
        except Exception:
            pass

    def close(self):
        try:
            self.cursor.close()
        except Exception:
            pass
        try:
            self.conn.close()
        except Exception:
            pass

@contextmanager
def transaction():
    """
    Context manager providing an atomic database transaction.
    Usage:
        with db_engine.transaction() as tx:
            tx.execute("INSERT INTO ...", params)
            tx.execute("UPDATE ...", params)
        # Commits automatically on success, rolls back on exception
    """
    db_type, conn = get_connection(autocommit=False)
    tx = TransactionContext(db_type, conn)
    try:
        yield tx
        tx.commit()
    except Exception:
        tx.rollback()
        raise
    finally:
        tx.close()

def execute_query(query, params=None, fetch="all", fetchone=False):
    """
    Executes a single SQL query against the active database engine safely.
    Automatically adapts placeholders and returns typed dictionaries / scalar results.
    """
    db_type, conn = get_connection(autocommit=True)
    if params is None:
        params = ()

    if fetchone:
        fetch = "one"

    normalized = normalize_query_for_engine(query, db_type)
    q_upper = normalized.strip().upper()

    if fetch == "all":
        if q_upper.startswith("INSERT"):
            fetch = "lastrowid"
        elif q_upper.startswith("UPDATE") or q_upper.startswith("DELETE"):
            fetch = "rowcount"

    try:
        if db_type == "mysql":
            with conn.cursor() as cursor:
                cursor.execute(normalized, params)
                if fetch == "all":
                    res = cursor.fetchall()
                    return [dict(row) for row in res]
                elif fetch == "one":
                    res = cursor.fetchone()
                    return dict(res) if res else None
                elif fetch == "lastrowid":
                    return cursor.lastrowid
                else:
                    return cursor.rowcount
        else:
            cursor = conn.cursor()
            cursor.execute(normalized, params)
            conn.commit()

            if fetch == "all":
                res = cursor.fetchall()
                return [dict(row) for row in res]
            elif fetch == "one":
                res = cursor.fetchone()
                return dict(res) if res else None
            elif fetch == "lastrowid":
                return cursor.lastrowid
            else:
                return cursor.rowcount
    finally:
        conn.close()

def execute_script(sql_script):
    """
    Executes a multi-statement SQL script (DDL/DML) on the active engine.
    """
    db_type, conn = get_connection(autocommit=True)
    try:
        # Strip comments and split by semicolon
        lines = [line for line in sql_script.splitlines() if not line.strip().startswith("--")]
        clean_script = "\n".join(lines)
        statements = [s.strip() for s in clean_script.split(";") if s.strip()]

        if db_type == "mysql":
            with conn.cursor() as cursor:
                for stmt in statements:
                    try:
                        cursor.execute(stmt)
                    except pymysql.err.OperationalError as e:
                        # Error 1061: Duplicate key name (index exists), 1050: Table already exists
                        if e.args[0] in (1061, 1050, 1060):
                            pass
                        else:
                            raise
        else:
            cursor = conn.cursor()
            for stmt in statements:
                stmt_clean = stmt.replace("`condition`", "condition")
                cursor.execute(stmt_clean)
            conn.commit()
    finally:
        conn.close()

def get_engine_status():
    """
    Returns active database engine health status (with masked credentials).
    """
    db_type, conn = get_connection()
    status = {
        "engine": db_type.upper(),
        "host": MYSQL_HOST if db_type == "mysql" else "local_file",
        "database": MYSQL_DB if db_type == "mysql" else "campuslink_umat.db",
        "user": MYSQL_USER if db_type == "mysql" else "local",
        "status": "Connected",
        "mysql_available": _mysql_available,
        "mode": "Production (MySQL)" if db_type == "mysql" else "Development/Fallback (SQLite 3)"
    }
    conn.close()
    return status

def check_database_health():
    """
    Executes a SELECT 1; ping query against the active database engine to measure latency and health.
    """
    import time
    try:
        start = time.perf_counter()
        db_type, conn = get_connection()
        if db_type == "mysql":
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            cursor.fetchone()
        conn.close()
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "healthy",
            "engine": db_type.upper(),
            "mode": "Production (MySQL)" if db_type == "mysql" else "Development/Fallback (SQLite 3)",
            "latency_ms": latency_ms
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": None
        }

