# tests/test_auth.py
import pytest
from app import db
from app.models import User

# test_auth.py 内のすべてのテストは、conftest.py の app, client, new_user_data, logged_in_client フィクスチャを利用できる

def test_register_page(client):
    """新規登録ページにアクセスできるかテスト"""
    response = client.get('/auth/register')
    assert response.status_code == 200
    assert "ユーザー登録".encode('utf-8') in response.data # ページの内容に「新規登録」という文字列が含まれるか

def test_register_new_user_data(client):
    """新しいユーザーが正常に登録できるかテスト"""
    response = client.post('/auth/register', data={
        'username': 'newuser',
        'name': 'New User',
        'email': 'newuser@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True) # リダイレクトを自動的に追跡

    print(response.data.decode('utf-8'))
    
    assert response.status_code == 200
    assert "アカウントが作成されました".encode('utf-8') # 成功メッセージ
    
    # データベースにユーザーが追加されたことを確認
    with client.application.app_context():
        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert user.email == 'newuser@example.com'

def test_register_duplicate_username(client, new_user_data):
    """重複ユーザー名での登録が拒否されるかテスト"""
    # new_user_dataフィクスチャにより、testuserが事前にDBに登録される
    response = client.post('/auth/register', data={
        'username': 'testuser', # 既存のユーザー名
        'name': 'New User',
        'email': 'test2@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)

    print(response.data.decode('utf-8'))
    
    assert response.status_code == 200
    assert "このユーザー名は既に使われています。".encode('utf-8') in response.data # エラーメッセージ
    
    # データベースに新しいユーザーが追加されていないことを確認
    with client.application.app_context():
        count = User.query.filter_by(username='testuser').count()
        assert count == 1 # 重複ユーザーは追加されていない

def test_login_valid_credentials(client, new_user_data):
    """有効な認証情報でログインできるかテスト"""
    # new_user_dataフィクスチャにより、testuserが事前にDBに登録される
    response = client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "ログインしました".encode('utf-8') # 成功メッセージ
    assert "ログアウト".encode('utf-8') # ログイン後に表示される要素

def test_login_invalid_password(client, new_user_data):
    """無効なパスワードでログインできないかテスト"""
    # new_user_dataフィクスチャにより、testuserが事前にDBに登録される
    response = client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "ユーザー名またはパスワードが正しくありません。".encode('utf-8') # エラーメッセージ
    assert "ログイン".encode('utf-8') # ログインページに留まっていることの確認

def test_logout(logged_in_client):
    """ログアウトできるかテスト"""
    response = logged_in_client.get('/auth/logout', follow_redirects=True)
    
    assert response.status_code == 200
    assert "ログアウトしました。" .encode('utf-8') # 成功メッセージ
    assert "ログイン".encode('utf-8') # ログインページに戻ったことの確認