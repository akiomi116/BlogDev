# F:\dev\BrogDev\app\cli.py

import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models import Role, User # UserモデルとRoleモデルをインポート
from werkzeug.security import generate_password_hash # パスワードハッシュ化のためにインポート
import os # 環境変数を取得するためにインポート

@click.group()
def init():
    """Database initialization commands."""
    pass

@init.command("roles")
@with_appcontext
def init_roles():
    """Create initial roles if they don't exist."""
    if Role.query.count() == 0:
        admin_role = Role(name='admin', description='Administrator with full access.')
        poster_role = Role(name='poster', description='User who can create and manage posts.')
        user_role = Role(name='user', description='Standard user with view access.')

        db.session.add_all([admin_role, poster_role, user_role])
        db.session.commit()
        click.echo("Default roles (admin, poster, user) created.")
    else:
        click.echo("Roles already exist. Skipping creation.")

# --- ここから新しいコマンドを追加 ---
@init.command("admin-user")
@click.option('--username', default='admin', help='Username for the admin user.')
@click.option('--email', default='admin@example.com', help='Email for the admin user.')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True,
              help='Password for the admin user.')
@with_appcontext
def init_admin_user(username, email, password):
    """Create an initial admin user."""
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        click.echo("Admin role not found. Please run 'flask init roles' first.", err=True)
        return

    if User.query.filter_by(username=username).first():
        click.echo(f"User '{username}' already exists. Skipping creation.", err=True)
        return

    try:
        hashed_password = generate_password_hash(password)
        admin_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            role_id=admin_role.id # admin_role.id を直接設定
        )
        db.session.add(admin_user)
        db.session.commit()
        click.echo(f"Admin user '{username}' created with email '{email}'.")
    except Exception as e:
        db.session.rollback()
        click.echo(f"Error creating admin user: {e}", err=True)
        click.echo("Please ensure roles are initialized and try again.", err=True)

# --- オプション: 全ての初期化を一括で行うコマンド ---
@init.command("all")
@with_appcontext
def init_all():
    """Create all initial data (roles, admin user)."""
    click.echo("Running all initial data setup...")

    # ロールを初期化
    click.invoke(init_roles)

    # 管理者ユーザーを初期化 (パスワードは対話形式で入力)
    click.echo("Creating admin user...")
    # ここで admin-user コマンドを呼び出すが、パスワードは対話形式で入力させる
    # click.invoke はオプションの値を渡すことができる
    # プロンプトを強制するには click.prompt を使う
    admin_username = click.prompt("Enter admin username", default='admin')
    admin_email = click.prompt("Enter admin email", default='admin@example.com')
    admin_password = click.prompt("Enter admin password", hide_input=True, confirmation_prompt=True)

    # generate_password_hash を直接使用
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        click.echo("Admin role not found. Cannot create admin user. Please run 'flask init roles' first if you skipped it.", err=True)
        return

    if User.query.filter_by(username=admin_username).first():
        click.echo(f"User '{admin_username}' already exists. Skipping admin user creation.", err=True)
    else:
        try:
            hashed_password = generate_password_hash(admin_password)
            admin_user = User(
                username=admin_username,
                email=admin_email,
                password_hash=hashed_password,
                role_id=admin_role.id
            )
            db.session.add(admin_user)
            db.session.commit()
            click.echo(f"Admin user '{admin_username}' created successfully.")
        except Exception as e:
            db.session.rollback()
            click.echo(f"Error creating admin user: {e}", err=True)
            click.echo("Database rollback performed.", err=True)

    click.echo("Initial data setup complete.")