# app/database.py
"""
データベースインスタンスを定義するモジュール
循環参照を避けるため、dbインスタンスを独立したモジュールに配置
"""

from flask_sqlalchemy import SQLAlchemy

# データベースインスタンスを作成
db = SQLAlchemy()