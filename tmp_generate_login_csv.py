import sqlite3
import csv

def generate_login_csv():
    conn = sqlite3.connect('db/complaints.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    credentials = []

    # 1. Agents (Admin, Supervisor, Worker)
    cursor.execute("SELECT agent_id, name, role, department FROM agents")
    for row in cursor.fetchall():
        role = row['role'].capitalize()
        dept = row['department']
        name = row['name']
        uid = row['agent_id']
        
        # Determine password based on known logic
        if uid == "AGT0001":
            password = "admin123"
        else:
            password = "password"
            
        credentials.append({
            'Role': f"{role} ({dept})",
            'Name': name,
            'Username/ID': uid,
            'Password': password
        })

    # 2. Citizens
    cursor.execute("SELECT name, identity_id FROM users")
    for row in cursor.fetchall():
        credentials.append({
            'Role': 'Citizen',
            'Name': row['name'],
            'Username/ID': row['identity_id'],
            'Password': "Check your registration (e.g. 123456)"
        })

    # Write to CSV
    filename = 'login_credentials_all.csv'
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Role', 'Name', 'Username/ID', 'Password'])
        writer.writeheader()
        writer.writerows(credentials)
        
    print(f"Generated {filename} with {len(credentials)} entries.")
    conn.close()

if __name__ == "__main__":
    generate_login_csv()
