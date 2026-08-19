"""
rollback_phase1.py
------------------
Restores the database to the pre-Phase 1 snapshot state.
"""
import os
import shutil

DB_DIR = os.path.dirname(os.path.abspath(__file__))
ACTIVE_DB = os.path.join(DB_DIR, "campuslink_umat.db")
BACKUP_DB = os.path.join(DB_DIR, "backup_pre_phase1.db")

def rollback():
    if os.path.exists(BACKUP_DB):
        shutil.copy2(BACKUP_DB, ACTIVE_DB)
        print(f"[ROLLBACK SUCCESS] Restored {ACTIVE_DB} from {BACKUP_DB}")
    else:
        print(f"[ROLLBACK ERROR] Backup snapshot {BACKUP_DB} not found!")

if __name__ == "__main__":
    rollback()
