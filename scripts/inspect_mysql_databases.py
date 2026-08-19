"""
scripts/inspect_mysql_databases.py
----------------------------------
Read-only inspection script to list MySQL databases and confirm target isolation.
Does NOT modify or drop any database or data.
"""
import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

def _load_credentials():
    """Checks os.environ, .env file, and Windows User Environment Registry."""
    # 1. Check .env file
    env_file = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k not in os.environ:
                        os.environ[k] = v
                        
    # 2. Check Windows User Registry
    if "MYSQL_PASSWORD" not in os.environ and sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                for var in ["MYSQL_PASSWORD", "MYSQL_USER", "MYSQL_HOST", "MYSQL_PORT", "MYSQL_DB"]:
                    try:
                        val, _ = winreg.QueryValueEx(key, var)
                        if var not in os.environ:
                            os.environ[var] = str(val)
                    except FileNotFoundError:
                        pass
        except Exception:
            pass

def inspect_databases():
    _load_credentials()
    
    host = os.environ.get("MYSQL_HOST", "localhost")
    port = int(os.environ.get("MYSQL_PORT", 3306))
    user = os.environ.get("MYSQL_USER", "root")
    password = os.environ.get("MYSQL_PASSWORD", "")
    target_db = os.environ.get("MYSQL_DB", "campuslink_umat")
    
    if not password:
        print("[!] MYSQL_PASSWORD was not detected in environment or .env file.")
        print("\nTo provide the credentials securely, choose either option:")
        print("  Option 1 (PowerShell User Variable):")
        print('    [System.Environment]::SetEnvironmentVariable("MYSQL_PASSWORD", "<your_password>", "User")')
        print('    [System.Environment]::SetEnvironmentVariable("MYSQL_USER", "root", "User")')
        print("  Option 2 (Create .env file in project root):")
        print("    MYSQL_PASSWORD=your_password_here")
        print("    MYSQL_USER=root")
        return False
        
    print(f"Connecting to MySQL at {host}:{port} as user '{user}'...")
    try:
        import pymysql
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        with conn.cursor() as cursor:
            cursor.execute("SHOW DATABASES;")
            databases = cursor.fetchall()
            
        conn.close()
        
        db_list = [d[list(d.keys())[0]] for d in databases]
        print("\n=== CURRENT MYSQL DATABASES ON HOST ===")
        for db in db_list:
            marker = " <-- TARGET ISOLATION DATABASE" if db == target_db else ""
            print(f" - {db}{marker}")
            
        print("\n=== DATABASE ISOLATION VERIFICATION ===")
        print(f"Target Database: '{target_db}'")
        if target_db in db_list:
            print(f"Status: Database '{target_db}' ALREADY EXISTS on this MySQL server.")
            print(f"Note: Verification will operate strictly inside '{target_db}'.")
        else:
            print(f"Status: Database '{target_db}' does NOT yet exist and will be created fresh in isolation.")
            
        print("\nSafety Confirmation: System databases (information_schema, mysql, performance_schema, sys) and other user databases will remain completely untouched.")
        return True
    except Exception as e:
        print(f"\n[!] MySQL Connection Failed: {e}")
        return False

if __name__ == "__main__":
    inspect_databases()
