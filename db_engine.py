import os
import sqlite3
import pymysql
import pymysql.cursors

# Environment Configuration
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DB = os.environ.get("MYSQL_DB", "campuslink_umat")
USE_MYSQL = os.environ.get("USE_MYSQL", "true").lower() in ("true", "1", "yes")

# SQLite Fallback Path
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "campuslink_umat.db")

_mysql_warning_shown = False

def set_mysql_credentials(host=None, port=None, user=None, password=None, database=None):
    """
    Updates MySQL credentials dynamically at runtime.
    """
    global MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, _mysql_warning_shown
    if host is not None: MYSQL_HOST = host
    if port is not None: MYSQL_PORT = int(port)
    if user is not None: MYSQL_USER = user
    if password is not None: MYSQL_PASSWORD = password
    if database is not None: MYSQL_DB = database
    _mysql_warning_shown = False

def get_connection():
    """
    Returns an active database connection.
    Attempts MySQL first if configured, falls back seamlessly to SQLite.
    """
    global _mysql_warning_shown
    if USE_MYSQL:
        try:
            conn = pymysql.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            return ("mysql", conn)
        except Exception as e:
            try:
                conn_raw = pymysql.connect(
                    host=MYSQL_HOST,
                    port=MYSQL_PORT,
                    user=MYSQL_USER,
                    password=MYSQL_PASSWORD,
                    charset='utf8mb4',
                    autocommit=True
                )
                with conn_raw.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DB} DEFAULT CHARACTER SET utf8mb4;")
                conn_raw.close()
                
                conn = pymysql.connect(
                    host=MYSQL_HOST,
                    port=MYSQL_PORT,
                    user=MYSQL_USER,
                    password=MYSQL_PASSWORD,
                    database=MYSQL_DB,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=True
                )
                return ("mysql", conn)
            except Exception as inner_e:
                if not _mysql_warning_shown:
                    print(f"[DB ENGINE INFO] MySQL unavailable ({inner_e}). Operating on SQLite engine.")
                    _mysql_warning_shown = True

    # SQLite Fallback
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return ("sqlite", conn)

def execute_query(query, params=None, fetch="all", fetchone=False):
    """
    Executes a SQL query against the active database engine.
    Automatically adapts placeholders ('?' for SQLite vs '%s' for MySQL).
    Auto-detects INSERT/UPDATE/DELETE queries to return lastrowid or rowcount.
    """
    db_type, conn = get_connection()
    if params is None:
        params = ()

    if fetchone:
        fetch = "one"

    # Auto-detect statement type if fetch parameter was left as default "all"
    q_upper = query.strip().upper()
    if fetch == "all":
        if q_upper.startswith("INSERT"):
            fetch = "lastrowid"
        elif q_upper.startswith("UPDATE") or q_upper.startswith("DELETE"):
            fetch = "rowcount"

    try:
        if db_type == "mysql":
            mysql_query = query.replace("?", "%s")
            with conn.cursor() as cursor:
                cursor.execute(mysql_query, params)
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
            # For SQLite, remove MySQL backticks if present
            sqlite_query = query.replace("`condition`", "condition")
            cursor = conn.cursor()
            cursor.execute(sqlite_query, params)
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

def get_engine_status():
    """
    Returns active database engine health status.
    """
    db_type, conn = get_connection()
    status = {
        "engine": db_type.upper(),
        "host": MYSQL_HOST if db_type == "mysql" else SQLITE_DB_PATH,
        "database": MYSQL_DB if db_type == "mysql" else "campuslink_umat.db",
        "user": MYSQL_USER if db_type == "mysql" else "local",
        "status": "Connected"
    }
    conn.close()
    return status
