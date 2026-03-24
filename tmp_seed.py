import sqlite3, hashlib, sys
sys.path.insert(0, '.')

conn = sqlite3.connect('db/complaints.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

pw = hashlib.sha256('test1234'.encode()).hexdigest()
cur.execute(
    "INSERT OR IGNORE INTO users (name, email, password_hash, city, pincode, identity_id) VALUES (?, ?, ?, ?, ?, ?)",
    ('Test Citizen', 'test@citizen.com', pw, 'Kolhapur', '416001', '123456789012')
)
conn.commit()

cur.execute("SELECT id, name, email FROM users WHERE email='test@citizen.com'")
row = dict(cur.fetchone())
print(row)
conn.close()
