import sqlite3
import hashlib
import json

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

DEPARTMENTS = [
    "Roads & Infrastructure",
    "Electricity & Streetlights",
    "Sanitation & Waste",
    "Water Supply",
    "Drainage & Sewerage",
    "Parks & Tree Maintenance",
    "Traffic Management",
    "Public Safety & General"
]

def populate():
    conn = sqlite3.connect('db/complaints.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get max ID and AGT ID
    cursor.execute("SELECT MAX(id) as max_id FROM agents")
    max_id = cursor.fetchone()['max_id'] or 0
    
    cursor.execute("SELECT agent_id FROM agents WHERE agent_id LIKE 'AGT%' ORDER BY agent_id DESC LIMIT 1")
    row = cursor.fetchone()
    last_agt_num = int(row['agent_id'][3:]) if row else 0

    password_hash = hash_password("password")

    new_agents = []
    
    for dept in DEPARTMENTS:
        # Check supervisor
        cursor.execute("SELECT COUNT(*) as cnt FROM agents WHERE department = ? AND role = 'supervisor'", (dept,))
        has_supervisor = cursor.fetchone()['cnt'] > 0
        
        if not has_supervisor:
            max_id += 1
            last_agt_num += 1
            agt_id = f"AGT{last_agt_num:04d}"
            name = f"Supervisor {dept[:10]}..." if len(dept) > 10 else f"Supervisor {dept}"
            new_agents.append((max_id, name, agt_id, password_hash, dept, 'supervisor', 'active'))
            print(f"Adding Supervisor for {dept}: {agt_id}")

        # Check workers
        cursor.execute("SELECT COUNT(*) as cnt FROM agents WHERE department = ? AND role = 'worker'", (dept,))
        worker_count = cursor.fetchone()['cnt']
        
        needed_workers = 3 - worker_count
        for i in range(needed_workers):
            max_id += 1
            last_agt_num += 1
            agt_id = f"AGT{last_agt_num:04d}"
            name = f"Worker {dept[:5]} {i+worker_count+1}"
            new_agents.append((max_id, name, agt_id, password_hash, dept, 'worker', 'active'))
            print(f"Adding Worker {i+worker_count+1} for {dept}: {agt_id}")

    if new_agents:
        cursor.executemany("""
            INSERT INTO agents (id, name, agent_id, password_hash, department, role, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, new_agents)
        conn.commit()
        print(f"Successfully added {len(new_agents)} agents.")
    else:
        print("No new agents needed.")

    conn.close()

if __name__ == "__main__":
    populate()
