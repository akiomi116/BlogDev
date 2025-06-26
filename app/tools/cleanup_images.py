import os
import sqlite3  # SQLiteの場合。他DBなら適宜修正

DB_PATH = 'F:\\dev\\BrogDev\\instance\\akiomi.db'  # 実際のDBパスに変更

def cleanup_images():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id, filepath, thumbnail_filepath FROM image")
    rows = cur.fetchall()

    deleted = 0
    for row in rows:
        id, filepath, thumbnail_filepath = row
        if not os.path.exists(filepath):
            print(f"削除: {id} (ファイルなし: {filepath})")
            cur.execute("DELETE FROM image WHERE id = ?", (id,))
            deleted += 1

    conn.commit()
    conn.close()
    print(f"削除完了: {deleted}件")

if __name__ == "__main__":
    cleanup_images()