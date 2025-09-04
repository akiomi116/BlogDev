# app/cli.py

import click
from flask.cli import with_appcontext
import os

from flask_security.utils import hash_password
from app.extensions import db, security
from app.models import User, Role




@click.group()
def init():
    """アプリケーションの初期化と管理コマンド."""
    pass


@init.command("roles")
@with_appcontext
def init_roles():
    """初期ロール（admin, poster, user）を作成します。"""
    security.datastore.find_or_create_role(
        'admin', description='Administrator with full access.'
    )
    security.datastore.find_or_create_role(
        'poster', description='User who can create and manage posts.'
    )
    security.datastore.find_or_create_role(
        'user', description='Standard user with view access.'
    )
    db.session.commit()
    click.echo("デフォルトロール (admin, poster, user) が作成または見つかりました。")


@init.command("admin-user")
@click.option('--username', default='admin', help='管理者ユーザーのユーザー名.')
@click.option('--email', default='admin@example.com', help='管理者ユーザーのメールアドレス.')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True,
            help='管理者ユーザーのパスワード.')
@with_appcontext
def init_admin_user(username, email, password):
    """初期管理者ユーザーを作成します。"""
    admin_role = security.datastore.find_role('admin')
    if not admin_role:
        click.echo(
            "Adminロールが見つかりません。先に 'flask init roles' を実行してください。",
            err=True
        )
        return

    if security.datastore.find_user(email=email):
        click.echo(f"ユーザー '{email}' は既に存在します。作成をスキップします。", err=True)
        return
    
    hashed_password = hash_password(password)

    try:
        security.datastore.create_user(
            username=username,
            email=email,
            password_hash=hashed_password,  # 生パスワードを渡すと自動でハッシュ化
            active=True,
            roles=[admin_role]
        )
        db.session.commit()
        click.echo(f"管理者ユーザー '{username}' (メール: '{email}') が正常に作成されました。")
    except Exception as e:
        db.session.rollback()
        click.echo(f"管理者ユーザーの作成中にエラーが発生しました: {e}", err=True)
        click.echo("データベースのロールバックが実行されました。", err=True)


@init.command("reset-db")
@click.option('--drop-db', is_flag=True, help='既存のデータベースを削除してから作成します。')
@click.option('--create-admin', is_flag=True, help='データベース作成後、管理者ユーザーを作成します。')
@click.option('--create-roles', is_flag=True, default=True, help='データベース作成後、デフォルトロールを作成します。')
@with_appcontext
@click.pass_context
def reset_db(ctx, drop_db, create_admin, create_roles):
    """データベースを再作成し、オプションで初期データ（ロール、管理者ユーザー）を設定します。"""
    db_path = db.engine.url.database

    if drop_db:
        if os.path.exists(db_path):
            click.echo(f"既存のデータベースを削除中: {db_path}")
            os.remove(db_path)
        else:
            click.echo(f"データベースファイルが見つかりません: {db_path}。削除をスキップします。")

    click.echo("データベーステーブルを作成中...")
    db.create_all()

    if create_roles:
        click.echo("デフォルトロールを作成中...")
        ctx.invoke(init_roles)

    if create_admin:
        click.echo("管理者ユーザーを作成中...")
        admin_username = click.prompt("管理者ユーザーのユーザー名を入力", default='admin')
        admin_email = click.prompt("管理者ユーザーのメールアドレスを入力", default='admin@example.com')
        admin_password = click.prompt("管理者ユーザーのパスワードを入力", hide_input=True, confirmation_prompt=True)
        ctx.invoke(init_admin_user, username=admin_username, email=admin_email, password=admin_password)

    click.echo("データベースと初期設定が完了しました。")


@init.command("all")
@click.option('--drop-db', is_flag=True, help='既存のデータベースを削除してから作成します。')
@with_appcontext
@click.pass_context
def init_all(ctx, drop_db):
    """全ての初期データ（ロール、管理者ユーザー）を設定します。"""
    click.echo("全ての初期データ設定を実行中...")
    ctx.invoke(reset_db, drop_db=drop_db, create_roles=True, create_admin=True)
    click.echo("全ての初期データ設定が完了しました。")
