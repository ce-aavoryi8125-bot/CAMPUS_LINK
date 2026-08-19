"""
test_stage1_1_db_engine.py
--------------------------
Targeted unit & integration tests for upgraded db_engine.py.
Verifies connection routing, query execution, atomic transactions, dialect normalization, and rollback.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import db_engine

class TestDBEngineStage1(unittest.TestCase):

    def test_01_engine_status(self):
        status = db_engine.get_engine_status()
        self.assertIn("engine", status)
        self.assertIn(status["engine"], ["SQLITE", "MYSQL"])
        self.assertEqual(status["status"], "Connected")
        self.assertIn("mode", status)
        print(f"  [OK] PASS  |  Engine status: {status['engine']} ({status['mode']})")

    def test_02_connection_acquisition(self):
        db_type, conn = db_engine.get_connection()
        self.assertIn(db_type, ["sqlite", "mysql"])
        self.assertIsNotNone(conn)
        conn.close()
        print(f"  [OK] PASS  |  Connection acquisition: {db_type} connection created and closed")

    def test_03_query_execution_fetch_all(self):
        res = db_engine.execute_query("SELECT user_id, name, email FROM users ORDER BY user_id LIMIT 3;", fetch="all")
        self.assertIsInstance(res, list)
        self.assertGreater(len(res), 0)
        self.assertIn("user_id", res[0])
        self.assertIn("name", res[0])
        self.assertIn("email", res[0])
        print(f"  [OK] PASS  |  execute_query(fetch='all'): Returned {len(res)} dict rows")

    def test_04_query_execution_fetch_one(self):
        res = db_engine.execute_query("SELECT user_id, name, email FROM users WHERE user_id = ?;", (1,), fetchone=True)
        self.assertIsInstance(res, dict)
        self.assertEqual(res["user_id"], 1)
        self.assertIn("name", res)
        print(f"  [OK] PASS  |  execute_query(fetchone=True): Retrieved user #{res['user_id']} ({res['name']})")

    def test_05_dialect_normalization_placeholders(self):
        sqlite_q = db_engine.normalize_query_for_engine("SELECT * FROM users WHERE user_id = ? AND email = ?;", "sqlite")
        mysql_q = db_engine.normalize_query_for_engine("SELECT * FROM users WHERE user_id = ? AND email = ?;", "mysql")
        self.assertIn("?", sqlite_q)
        self.assertIn("%s", mysql_q)
        print(f"  [OK] PASS  |  Dialect normalization: SQLite uses '?' and MySQL uses '%s'")

    def test_06_dialect_normalization_insert_ignore(self):
        sqlite_q = db_engine.normalize_query_for_engine("INSERT IGNORE INTO wishlist (user_id) VALUES (?);", "sqlite")
        mysql_q = db_engine.normalize_query_for_engine("INSERT OR IGNORE INTO wishlist (user_id) VALUES (?);", "mysql")
        self.assertIn("INSERT OR IGNORE", sqlite_q)
        self.assertIn("INSERT IGNORE", mysql_q)
        print(f"  [OK] PASS  |  Dialect normalization: 'INSERT OR IGNORE' (SQLite) vs 'INSERT IGNORE' (MySQL)")

    def test_07_atomic_transaction_commit(self):
        # Insert a temporary test user inside a transaction and verify commit
        with db_engine.transaction() as tx:
            new_id = tx.execute(
                "INSERT INTO users (name, email, password_hash, phone, department) VALUES (?, ?, ?, ?, ?);",
                ("Atomic Tx User", "atomic_tx@student.umat.edu.gh", "hash123", "+233240000001", "Computer Science"),
                fetch="lastrowid"
            )
            self.assertGreater(new_id, 0)
            
            # Verify within transaction
            row = tx.execute("SELECT name FROM users WHERE user_id = ?;", (new_id,), fetchone=True)
            self.assertEqual(row["name"], "Atomic Tx User")

        # Verify persisted outside transaction
        check_row = db_engine.execute_query("SELECT user_id, name FROM users WHERE email = ?;", ("atomic_tx@student.umat.edu.gh",), fetchone=True)
        self.assertIsNotNone(check_row)
        self.assertEqual(check_row["name"], "Atomic Tx User")

        # Cleanup
        db_engine.execute_query("DELETE FROM users WHERE email = ?;", ("atomic_tx@student.umat.edu.gh",))
        print(f"  [OK] PASS  |  Atomic transaction: Successful multi-step commit verified")

    def test_08_atomic_transaction_rollback(self):
        # Attempt transaction where second statement fails
        initial_count = db_engine.execute_query("SELECT COUNT(*) as count FROM users WHERE email LIKE '%rollback%';", fetchone=True)["count"]
        
        with self.assertRaises(Exception):
            with db_engine.transaction() as tx:
                tx.execute(
                    "INSERT INTO users (name, email, password_hash, phone, department) VALUES (?, ?, ?, ?, ?);",
                    ("Rollback User", "rollback_user@student.umat.edu.gh", "hash123", "+233240000002", "Mining Engineering"),
                    fetch="lastrowid"
                )
                # Intentionally trigger constraint error (duplicate email)
                tx.execute(
                    "INSERT INTO users (name, email, password_hash, phone, department) VALUES (?, ?, ?, ?, ?);",
                    ("Duplicate Rollback User", "rollback_user@student.umat.edu.gh", "hash123", "+233240000003", "Mining Engineering"),
                    fetch="lastrowid"
                )

        # Verify rollback: record was not inserted
        final_count = db_engine.execute_query("SELECT COUNT(*) as count FROM users WHERE email LIKE '%rollback%';", fetchone=True)["count"]
        self.assertEqual(final_count, initial_count)
        print(f"  [OK] PASS  |  Atomic transaction: Automatic rollback on exception verified")

if __name__ == '__main__':
    print("========================================================================")
    print("   CampusLink Stage 1.1: Database Engine Unit Test Suite")
    print("========================================================================")
    unittest.main()
