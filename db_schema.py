# Compatibility shim forwarding to database/database_schema.py
from database.database_schema import *

if __name__ == "__main__":
    create_tables()
