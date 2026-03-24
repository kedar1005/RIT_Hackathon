import sqlite3
import csv
import os

def export_db():
    conn = sqlite3.connect('db/complaints.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row['name'] for row in cursor.fetchall()]

    for table in tables:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()

        if rows:
            filename = f"export_{table}.csv"
            keys = rows[0].keys()
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                dict_writer = csv.DictWriter(f, fieldnames=keys)
                dict_writer.writeheader()
                dict_writer.writerows([dict(r) for r in rows])
            print(f"Exported {table} to {filename} ({len(rows)} rows)")
        else:
            print(f"Table {table} is empty, skipping.")

    conn.close()

if __name__ == "__main__":
    export_db()
