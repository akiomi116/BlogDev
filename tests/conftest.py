# tests/conftest.py
import sys
import os

# プロジェクトのルートディレクトリをPythonのパスに追加
# このファイル (conftest.py) のディレクトリから2階層上 (F:\dev\BrogDev)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db # 元々ある行
from app.models import User, Post, Category, Tag # 必要に応じてインポート

import pytest

@pytest.fixture(scope='session')
def app():
    """テスト用Flaskアプリケーションのインスタンスを生成するフィクスチャ"""
    app = create_app() # あなたのcreate_app関数を呼び出す
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", # メモリ上のDBを使用
        "WTF_CSRF_ENABLED": False # テスト中はCSRFを無効にすることが多い
    })
    with app.app_context():
        db.create_all() # Create tables once for the session
    yield app
    with app.app_context():
        db.drop_all() # Drop tables once after the session

@pytest.fixture(scope='function')
def client(app):
    """テストクライアントを生成するフィクスチャ"""
    return app.test_client()

@pytest.fixture(scope='function')
def runner(app):
    """CLIコマンドランナーを生成するフィクスチャ"""
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def new_user_data():
    """テスト用のユーザーデータを辞書として作成するフィクスチャ (DBには追加しない)"""
    return {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123'
    }

@pytest.fixture(scope='function')
def session(app):
    """各テスト関数でトランザクションを管理するフィクスチャ"""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        db.session.configure(bind=connection)

        yield db.session

        transaction.rollback()
        connection.close()

@pytest.fixture
def new_user():
    """テスト用のユーザーデータを作成するフィクスチャ"""
    # Userインスタンスを、'username'と'email'引数のみで初期化
    # 'password'引数は削除します
    user = User(username='testuser', email='test@example.com')

    # Userモデルの set_password メソッドを呼び出し、生パスワードを設定
    user.set_password('password123') 

    # ユーザーにロールが必須の場合はここで設定（もしUserモデルにroleのデフォルト値がない場合）
    # user.role = 'user' # 必要であれば追加

    return user

@pytest.fixture(scope='function')
def logged_in_client(client, app, new_user_data, session): # Added session
    """ログイン済みのテストクライアントを生成するフィクスチャ"""

    # Create user within the session context
    existing_user = User.query.filter_by(username=new_user_data['username']).first()
    if existing_user:
        session.delete(existing_user)
        session.commit() # Commit deletion

    user = User(username=new_user_data['username'], email=new_user_data['email'])
    user.set_password(new_user_data['password'])
    session.add(user)
    session.commit() # Commit user creation

    # ログインリクエストを送信
    response = client.post('/auth/login', data={
        'username': new_user_data['username'],
        'password': new_user_data['password']
    }, follow_redirects=True)

    yield client