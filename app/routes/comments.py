# F:\dev\BrogDev\app\routes\comments.py

from flask import Blueprint, render_template, flash, redirect, url_for, current_app, abort
from flask_login import login_required, current_user
from app.models import Comment # Commentモデルをインポート
from app.extensions import db # dbがapp.extensionsからインポートされていることを確認
import os

comments_bp = Blueprint(
    'comments',
    __name__,
    url_prefix='/admin/comments', # URLとしては /admin/comments から始まる
    # template_folderのパスをadmin/templatesを指すように調整
    # app/admin/templates を指すようにパスを調整
    template_folder=os.path.join(os.path.abspath(os.path.dirname(__file__)), '../../admin/templates')
)

@comments_bp.route('/comments', methods=['GET'])
@login_required
def list_comments():
    """
    コメントの一覧を表示します。
    adminロールのユーザーのみアクセス可能です。
    """
    if not current_user.is_authenticated or \
       not hasattr(current_user, 'role') or \
       not current_user.role or \
       current_user.role.name != 'admin': # comments管理はadminのみとする
        flash('この操作を行う権限がありません。', 'danger')
        current_app.logger.warning(f"ACCESS_DENIED: User {current_user.id} attempted to access list_comments without admin role.")
        abort(403)

    comments = Comment.query.order_by(Comment.created_at.desc()).all()
    return render_template('admin/list_comments.html', comments=comments)

# コメント承認/非承認のルート (adminのみ)
@comments_bp.route('/toggle_approval/<uuid:comment_id>', methods=['POST'])
@login_required
def toggle_approval(comment_id):
    if not current_user.is_authenticated or \
       not hasattr(current_user, 'role') or \
       not current_user.role or \
       current_user.role.name != 'admin':
        flash('この操作を行う権限がありません。', 'danger')
        abort(403)

    comment = db.session.get(Comment, comment_id)
    if comment is None:
        flash('コメントが見つかりませんでした。', 'danger')
        abort(404)

    try:
        comment.is_approved = not comment.is_approved
        db.session.commit()
        flash(f"コメント '{comment.id}' の承認ステータスを {'承認済み' if comment.is_approved else '未承認'} に変更しました。", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'コメントの更新中にエラーが発生しました: {e}', 'danger')
        current_app.logger.error(f"Error toggling approval for comment {comment_id}: {e}", exc_info=True)
    
    return redirect(url_for('comments.list_comments'))

