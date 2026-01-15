"""
Простой скрипт для просмотра базы данных
"""
import sqlite3

conn = sqlite3.connect('autoimport.db')
cursor = conn.cursor()

print("=" * 60)
print("TABLES IN DATABASE")
print("=" * 60)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
for t in cursor.fetchall():
    print(f"  - {t[0]}")

print("\n" + "=" * 60)
print("CARS (first 10)")
print("=" * 60)
cursor.execute('''
    SELECT id, brand, model, year, price_rub, country, body_type 
    FROM cars 
    ORDER BY price_rub 
    LIMIT 10
''')
print(f"{'ID':>4} | {'Brand':<15} | {'Model':<15} | {'Year'} | {'Price RUB':>14} | {'Country':<10} | {'Body'}")
print("-" * 95)
for row in cursor.fetchall():
    print(f"{row[0]:>4} | {row[1]:<15} | {row[2]:<15} | {row[3]} | {row[4]:>14,} | {row[5]:<10} | {row[6]}")

print("\n" + "=" * 60)
print("CARS STATS")
print("=" * 60)
cursor.execute("SELECT COUNT(*) FROM cars")
print(f"Total cars: {cursor.fetchone()[0]}")

cursor.execute("SELECT brand, COUNT(*) as cnt FROM cars GROUP BY brand ORDER BY cnt DESC")
print("\nBy brand:")
for row in cursor.fetchall():
    print(f"  {row[0]:<15}: {row[1]} cars")

cursor.execute("SELECT country, COUNT(*) as cnt FROM cars GROUP BY country ORDER BY cnt DESC")
print("\nBy country:")
for row in cursor.fetchall():
    print(f"  {row[0]:<10}: {row[1]} cars")

print("\n" + "=" * 60)
print("LEADS")
print("=" * 60)
cursor.execute("SELECT COUNT(*) FROM leads")
lead_count = cursor.fetchone()[0]
print(f"Total leads: {lead_count}")

if lead_count > 0:
    cursor.execute('''
        SELECT id, session_id, name, phone, car_brand, budget_max, qualification, status 
        FROM leads 
        ORDER BY id DESC 
        LIMIT 5
    ''')
    print("\nRecent leads:")
    for row in cursor.fetchall():
        print(f"  ID={row[0]}, session={row[1]}, name={row[2]}, phone={row[3]}")
        print(f"    brand={row[4]}, budget={row[5]}, qual={row[6]}, status={row[7]}")

print("\n" + "=" * 60)
print("CONVERSATIONS")
print("=" * 60)
cursor.execute("SELECT COUNT(*) FROM conversations")
conv_count = cursor.fetchone()[0]
print(f"Total messages: {conv_count}")

conn.close()
