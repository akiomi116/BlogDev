# F:\dev\BrogDev\populate_uniquifier.py (修正版)
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import uuid

# あなたのアプリの作成とdbのセットアップがapp/__init__.pyにあると仮定
from app import create_app, db
from app.models import User # Userモデルのファイルパスに合わせて調整してください

app = create_app() # Flaskアプリのインスタンスを作成

# ★このwithブロックを使用することで、app_context()のpush/popを手動で管理する必要がなくなります。★
with app.app_context():
    print("既存ユーザーのfs_uniquifierを設定中...")
    # fs_uniquifierが設定されていないユーザーを検索
    users_to_update = User.query.filter(User.fs_uniquifier == None).all()

    if not users_to_update:
        print("fs_uniquifierがNULLのユーザーは見つかりませんでした。すべて良好です！")
    else:
        for user in users_to_update:
            user.fs_uniquifier = str(uuid.uuid4())
            print(f"Updated user: {user.email}")
        db.session.commit()
        print(f"既存の{len(users_to_update)}人のユーザーのfs_uniquifierを正常に設定しました。")

# 手動のpop()は不要になります
# app.app_context().pop() # この行は削除する