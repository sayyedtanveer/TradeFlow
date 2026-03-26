import sqlite3

conn = sqlite3.connect('medtrack.db')
cur = conn.cursor()

# Get all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print("=== ALL TABLES ===")
if not tables:
    print("No tables found in database - need to run migrations")
else:
    for t in tables:
        print(f"  - {t[0]}")

# Check if tenants table exists
try:
    cur.execute('SELECT id, name FROM tenants LIMIT 5')
    print("\n=== TENANTS ===")
    for row in cur:
        print(f'ID: {row[0]}, Name: {row[1]}')
except Exception as e:
    print(f"\nError querying tenants: {e}")

# Check if users table exists
try:
    cur.execute('SELECT id, email, tenant_id FROM users WHERE email LIKE ?', ('%admin%',))
    print("\n=== ADMIN USERS ===")
    for row in cur:
        print(f'ID: {row[0]}, Email: {row[1]}, Tenant ID: {row[2]}')
except Exception as e:
    print(f"\nError querying users: {e}")

conn.close()
