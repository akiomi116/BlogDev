# F:\dev\BrogDev\app\routes\auth.py

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User, Role # Import Role
from app.extensions import db
from app.forms import LoginForm, RegistrationForm, ChangePasswordForm, ResetPasswordRequestForm, ResetPasswordForm
# from app.email import send_password_reset_email


bp = Blueprint('auth', __name__)

# @bp.route('/login', methods=['GET', 'POST'], endpoint='login') # ★追加: endpoint='login'
# def login():
#     if current_user.is_authenticated:
#         # 管理者ならadminダッシュボードへ、そうでなければhome.indexへ
#         if current_user.has_role('admin') or current_user.has_role('editor') or current_user.has_role('poster'):
#             flash('ログインしました。', 'info')
#             current_app.logger.info(f"User {current_user.username} logged in. Redirecting to admin.index")
#             return redirect(url_for('/admin/'))
#         else:
#             flash('ログインしました。', 'info')
#             current_app.logger.info(f"User {current_user.username} logged in. Redirecting to home.index")
#             return redirect(url_for('home.index'))
#     
#     if request.method == 'POST':
#         current_app.logger.debug(f"Request Headers: {request.headers}")
#         current_app.logger.debug(f"Request Form Data: {request.form}")
# 
#     form = LoginForm()
#     if form.validate_on_submit():
#         user = User.query.filter_by(email=form.email.data).first()
#         if user is None or not check_password_hash(user.password_hash, form.password.data):
#             flash('無効なメールアドレスまたはパスワードです。', 'danger')
#             return redirect(url_for('security.login'))
#         
#         login_user(user, remember=form.remember_me.data)
#         next_page = request.args.get('next')
#         # next_page が安全なURLであることを確認するロジックを追加することが望ましい
#         # 例えば werkzeug.utils.url_parse を使ってホスト名が同じか確認するなど
#         
#         # ログイン成功後のリダイレクト先を修正
#         if current_user.has_role('admin') or current_user.has_role('editor') or current_user.has_role('poster'):
#             flash('ログインしました。', 'info')
#             current_app.logger.info(f"User {user.username} logged in. Redirecting to admin.index")
#             return redirect(next_page or url_for('blog_admin_bp.index'))
#         else:
#             flash('ログインしました。', 'info')
#             current_app.logger.info(f"User {user.username} logged in. Redirecting to home.index")
#             return redirect(next_page or url_for('home.index'))
# 
#     if form.errors:
#         current_app.logger.error(f"Form validation errors: {form.errors}")
# 
#     return render_template('auth/login.html', title='ログイン', form=form)

@bp.route('/logout', endpoint='logout') # ★追加: endpoint='logout'
@login_required
def logout():
    logout_user()
    flash('ログアウトしました。', 'info')
    return redirect(url_for('home.index'))

@bp.route('/register', methods=['GET', 'POST'], endpoint='register') # ★追加: endpoint='register'
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data)
        )
        # フォームから選択されたロールを取得
        selected_role = form.role.data
        if selected_role:
            user.roles.append(selected_role)
        else:
            # ロールが選択されなかった場合のフォールバック（フォームで必須にしているので通常は通らない）
            user_role = Role.query.filter_by(name='user').first()
            if user_role:
                user.roles.append(user_role)
            else:
                current_app.logger.error("Default 'user' role not found and no role selected during registration.")
                flash('登録処理中にエラーが発生しました。', 'danger')
                return redirect(url_for('auth.register'))

        db.session.add(user)
        db.session.commit()
        flash('登録ありがとうございます！これでログインできます。', 'success')
        return redirect(url_for('security.login')) # 明示的にエンドポイント名を指定
    return render_template('auth/register.html', title='ユーザー登録', form=form)

@bp.route('/reset_password_request', methods=['GET', 'POST'], endpoint='reset_password_request') # ★追加: endpoint='reset_password_request'
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('home.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # send_password_reset_email(user)
            flash('パスワードリセットの手順をメールで送信しました。', 'info')
            return redirect(url_for('security.login')) # 明示的にエンドポイント名を指定
    return render_template('auth/reset_password_request.html', title='パスワードリセット', form=form)

# def send_password_reset_email(user):
#     token = user.get_reset_password_token()
#     msg = Message(
#         'パスワードリセットの依頼',
#         sender=current_app.config['MAIL_USERNAME'],
#         recipients=[user.email]
#     )
#     # url_for の呼び出しでブループリント名.エンドポイント名 を使用することを徹底
#     reset_url = url_for('auth.reset_password', token=token, _external=True) 
#     msg.body = render_template('email/reset_password.txt', user=user, reset_url=reset_url)
#     msg.html = render_template('email/reset_password.html', user=user, reset_url=reset_url)
#     mail.send(msg)

@bp.route('/reset_password/<token>', methods=['GET', 'POST'], endpoint='reset_password') # ★追加: endpoint='reset_password'
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('home.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        flash('無効なトークンまたは期限切れのトークンです。', 'danger')
        return redirect(url_for('auth.reset_password_request')) # 明示的にエンドポイント名を指定
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password_hash = generate_password_hash(form.password.data)
        db.session.commit()
        flash('パスワードがリセットされました。新しいパスワードでログインしてください。', 'success')
        return redirect(url_for('security.login')) # 明示的にエンドポイント名を指定
    return render_template('auth/reset_password.html', title='パスワードリセット', form=form)

@bp.route('/change_password', methods=['GET', 'POST'], endpoint='change_password') # ★追加: endpoint='change_password'
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not check_password_hash(current_user.password_hash, form.old_password.data):
            flash('現在のパスワードが間違っています。', 'danger')
            return redirect(url_for('auth.change_password')) # 明示的にエンドポイント名を指定
        
        current_user.password_hash = generate_password_hash(form.new_password.data)
        db.session.commit()
        flash('パスワードが正常に変更されました。', 'success')
        return redirect(url_for('home.index')) 
    return render_template('auth/change_password.html', title='パスワード変更', form=form)

@bp.route('/profile')
@login_required
def profile():
    # ユーザー自身のプロフィール情報を表示するテンプレートをレンダリング
    # 必要に応じて、ユーザー情報をテンプレートに渡す
    return render_template('auth/profile.html', user=current_user, title='プロフィール')
