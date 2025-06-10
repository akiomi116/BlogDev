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
        db.create_all() # テスト用DBにテーブルを作成
        yield app # アプリケーションインスタンスをテストに渡す
        db.drop_all() # テスト終了後にDBをクリア

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
def logged_in_client(client, app, new_user_data): # 'app' と 'new_user_data' を受け取る
    """ログイン済みのテストクライアントを生成するフィクスチャ"""

    # app_context内でユーザーを作成し、セッションにバインド
    with app.app_context():
        existing_user = User.query.filter_by(username=new_user_data['username']).first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()
        
        user = User(username=new_user_data['username'], email=new_user_data['email'])
        user.set_password(new_user_data['password'])
        db.session.add(user)
        db.session.commit() # コミット後、この user オブジェクトはデタッチされる可能性がある

        # ログイン後、ユーザー情報を再度DBから取得し直すことで、セッションにバインドされた状態のオブジェクトを保証
        # ただし、ログイン処理自体でセッションが生成・利用されるため、ここでの再取得は必須ではない場合も
        # 確実性を高めるためであれば検討
        # user_from_db = User.query.filter_by(username=new_user_data['username']).first()
        # if user_from_db:
        #    print(f"User from DB: {user_from_db}") # デバッグ用

    # ログインリクエストを送信
    # ここで new_user_data の辞書から直接 username を取得
    response = client.post('/auth/login', data={
        'username': new_user_data['username'], # 辞書からusernameを取得
        'password': new_user_data['password']
    }, follow_redirects=True)

    # yield で client を返し、テスト関数がこのクライアントを使用できるようにする
    yield client 

    # テスト終了後のクリーンアップ（オプションだが推奨）
    # 各テスト関数が独立して実行されるように、作成したユーザーを削除
    with app.app_context():
        user_to_delete = User.query.filter_by(username=new_user_data['username']).first()
        if user_to_delete:
            db.session.delete(user_to_delete)
            db.session.commit()