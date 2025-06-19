# F:\dev\BrogDev\app\routes\auth.py

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, Role
from app.extensions import db
from app.forms import LoginForm, AuthForm
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

# ログイン
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # ログイン済みの場合、ユーザーのロールに基づいてリダイレクト
        if current_user.role and current_user.role.name in ['admin', 'poster']:
            return redirect(url_for('blog_admin_bp.admin_dashboardindex')) # 管理者・投稿者は管理ダッシュボードへ
        else:
            return redirect(url_for('home.index')) # その他のユーザーは一般ホームへ（要 home.index ルートの定義）

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash('ログインしました。', 'success')
            next_page = request.args.get('next')
            current_app.logger.info(f"User {user.username} logged in. Redirecting to {next_page or 'home.dashboard'}")

            # ログイン成功後、ユーザーのロールに基づいてリダイレクト先を決定
            if user.role and user.role.name in ['admin', 'poster']:
                return redirect(next_page or url_for('blog_admin_bp.index')) # 管理者・投稿者は管理ダッシュボードへ
            else:
                return redirect(next_page or url_for('home.index')) # その他のユーザーは一般ホームへ

        else:
            flash('ユーザー名またはパスワードが正しくありません。', 'danger')
            current_app.logger.warning(f"Failed login attempt for username: {form.username.data}")
    return render_template('auth/login.html', form=form)


# ユーザー登録
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        # ログイン済みの場合、ユーザーのロールに基づいてリダイレクト
        if current_user.role and current_user.role.name in ['admin', 'poster']:
            return redirect(url_for('blog_admin_bp.admin_dashboard')) # 管理者・投稿者は管理ダッシュボードへ
        else:
            return redirect(url_for('home.index')) # その他のユーザーは一般ホームへ

    form = AuthForm()
    if form.validate_on_submit():
        default_role = Role.query.filter_by(name='user').first()
        if not default_role:
            default_role = Role(name='user')
            db.session.add(default_role)
            db.session.commit()
            logger.info("Default 'user' role created as it did not exist.")

        user = User(
            username=form.username.data,
            email=form.email.data,
            role=default_role
        )
        user.set_password(form.password.data)
        try:
            db.session.add(user)
            db.session.commit()
            flash('登録が完了しました。ログインしてください。', 'success')
            current_app.logger.info(f"New user {user.username} registered.")
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'登録中にエラーが発生しました: {e}', 'danger')
            current_app.logger.error(f"Error during user registration: {e}", exc_info=True)
            
    return render_template('auth/register.html', form=form)


# ログアウト
@auth_bp.route('/logout')
@login_required
def logout():
    current_app.logger.info(f"User {current_user.username} logged out.")
    logout_user()
    flash('ログアウトしました。', 'info')
    return redirect(url_for('auth.login'))