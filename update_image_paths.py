# update_image_paths.py
import os
from app import create_app
from app.extensions import db
from app.models import Image

def update_image_table_paths():
    app = create_app()
    with app.app_context(): # アプリケーションコンテキスト内でDB操作を実行
        print("Updating Image table records to remove path prefixes...")

        images = Image.query.all()
        updated_count = 0

        for image in images:
            original_filename = image.filename
            original_thumbnail_url = image.thumbnail_url

            # os.path.basename() を使ってパスからファイル名部分だけを抽出
            new_filename = os.path.basename(original_filename)
            new_thumbnail_url = os.path.basename(original_thumbnail_url)

            # 変更があった場合のみ更新
            if image.filename != new_filename or image.thumbnail_url != new_thumbnail_url:
                image.filename = new_filename
                image.thumbnail_url = new_thumbnail_url
                updated_count += 1
                print(f"  Updated: ID={image.id}, Old Filename='{original_filename}' -> New Filename='{new_filename}'")
                print(f"                     Old Thumb='{original_thumbnail_url}' -> New Thumb='{new_thumbnail_url}'")
            else:
                print(f"  No change: ID={image.id}, Filename='{original_filename}'")

        if updated_count > 0:
            try:
                db.session.commit()
                print(f"Successfully updated {updated_count} Image records in the database.")
            except Exception as e:
                db.session.rollback()
                print(f"Error committing changes: {e}")
                print("Database transaction rolled back.")
        else:
            print("No Image records needed updating (filenames already in correct format).")

        # db.session.remove() は with app.app_context(): ブロック内で自動的に処理されるため不要

    print("Database update script finished.")

if __name__ == '__main__':
    update_image_table_paths()