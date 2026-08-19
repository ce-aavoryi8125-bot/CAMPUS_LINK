import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campuslink_umat.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = [r[0] for r in cur.fetchall() if not r[0].startswith("sqlite_")]
print(f"DATABASE INSPECTION ({len(tables)} tables):")
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM {t};")
    cnt = cur.fetchone()[0]
    print(f"  {t}: {cnt} rows")
conn.close()
