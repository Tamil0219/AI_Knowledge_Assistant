import sqlite3

conn = sqlite3.connect('database/app.db')
cur = conn.cursor()
cur.execute("SELECT image_id,original_image_path,processed_image_path FROM ImageHistory WHERE user_id=(SELECT user_id FROM Users WHERE username='testuser')")
print(cur.fetchall())
conn.close()
