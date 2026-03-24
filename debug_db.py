from utils.data_utils import init_database, DB_PATH
import os

print(f"Initializing database at: {DB_PATH}")
init_database()
if os.path.exists(DB_PATH):
    print(f"✅ Database created successfully at {DB_PATH}")
else:
    print(f"❌ Database creation failed at {DB_PATH}")
