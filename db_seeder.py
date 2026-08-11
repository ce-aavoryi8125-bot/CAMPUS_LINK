# Compatibility shim forwarding to database/db_seeder.py
from database.db_seeder import *

if __name__ == "__main__":
    seed_database()
