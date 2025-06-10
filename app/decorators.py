# F:\dev\BrogDev\app\decorators.py

from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user
import logging

def roles_required(allowed_roles):
    """
    ユーザーが指定されたロールのいずれかを持っていることを要求するデコレータ。
    @login_required の後に適用することを想定しています。
    :param allowed_roles: 許可するロール名のリスト (例: ['admin', 'poster'])
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # ログイン済みであることを前提とするが、念のため再度チェック
            if not current_user.is_authenticated:
                flash('ログインが必要です。', 'warning')
                return redirect(url_for('auth.login'))

            # ユーザーがロールを持っていない、またはロール名が許可リストにない場合
            if not hasattr(current_user, 'role') or current_user.role is None or current_user.role.name not in allowed_roles:
                user_role_name = current_user.role.name if hasattr(current_user, 'role') and current_user.role else 'None'
                logging.warning(f"ACCESS_DENIED: User {current_user.id} ({user_role_name}) attempted to access {f.__name__} without sufficient role. Required: {allowed_roles}")
                flash('アクセス権限がありません。', 'danger')
                abort(403) # 403 Forbidden エラーを返す
            return f(*args, **kwargs)
        return decorated_function
    return decorator