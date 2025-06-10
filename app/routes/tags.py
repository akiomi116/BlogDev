from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Tag, Post, post_tags
from app.forms import TagForm
import os
import logging
import uuid
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

tags_bp = Blueprint(
    'tags',
    __name__,
    url_prefix='/admin/tags',
    template_folder=os.path.join(os.path.abspath(os.path.dirname(__file__)), '../admin/templates')
)

# タグ一覧表示
@tags_bp.route('/tags')
@login_required
def list_tags():
    # 権限チェック (posterまたはadmin)
    if not current_user.is_authenticated or \
       not hasattr(current_user, 'role') or \
       not current_user.role or \
       current_user.role.name not in ['admin', 'poster']:
        flash('この操作を行う権限がありません。', 'danger')
        current_app.logger.warning(f"ACCESS_DENIED: User {current_user.id if current_user.is_authenticated else 'Anonymous'} attempted to access list_tags without sufficient role.")
        abort(403)

    # 現在のユーザーのタグのみを取得
    tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name.asc()).all()
    return render_template('tags/list_tags.html', tags=tags)

# 新規タグ作成
@tags_bp.route('/tags/new', methods=['GET', 'POST'])
@login_required
def new_tag():
    # 権限チェック (posterまたはadmin)
    if not current_user.is_authenticated or \
       not hasattr(current_user, 'role') or \
       not current_user.role or \
       current_user.role.name not in ['admin', 'poster']:
        flash('この操作を行う権限がありません。', 'danger')
        current_app.logger.warning(f"ACCESS_DENIED: User {current_user.id if current_user.is_authenticated else 'Anonymous'} attempted to create new_tag without sufficient role.")
        abort(403)

    form = TagForm()
    
    if form.validate_on_submit():
        try:
            # スラッグの自動生成（簡易版）
            slug = form.name.data.lower().replace(' ', '-').replace('　', '-')
            
            new_tag = Tag(
                name=form.name.data,
                slug=slug,
                user_id=current_user.id
            )
            db.session.add(new_tag)
            db.session.commit()
            flash(f'タグ "{new_tag.name}" が正常に作成されました。', 'success')
            return redirect(url_for('tags.list_tags'))
        except IntegrityError as e:
            db.session.rollback()
            if 'name_user_id_uc' in str(e):
                flash('このタグ名は既に存在します。', 'danger')
            elif 'slug_user_id_uc' in str(e):
                flash('このスラッグは既に存在します。', 'danger')
            else:
                flash(f'タグの作成中にエラーが発生しました: {e}', 'danger')
            current_app.logger.error(f"IntegrityError creating new tag: {e}", exc_info=True)
        except Exception as e:
            db.session.rollback()
            flash(f'タグの作成中にエラーが発生しました: {e}', 'danger')
            current_app.logger.error(f"Error creating new tag: {e}", exc_info=True)
    
    return render_template('tags/new_tag.html', form=form, title='新しいタグを作成')

# タグ編集
@tags_bp.route('/tags/edit/<uuid:tag_id>', methods=['GET', 'POST'])
@login_required
def edit_tag(tag_id):
    tag = db.session.get(Tag, tag_id)
    if tag is None:
        abort(404)

    # 権限チェック（作成者または管理者のみ）
    if tag.user_id != current_user.id and \
       (not hasattr(current_user, 'role') or not current_user.role or current_user.role.name != 'admin'):
        flash('この操作を行う権限がありません。', 'danger')
        current_app.logger.warning(f"ACCESS_DENIED: User {current_user.id} attempted to edit tag {tag_id} without permission.")
        abort(403)

    form = TagForm(obj=tag)  # 既存のタグデータでフォームを初期化

    if form.validate_on_submit():
        try:
            # スラッグの自動生成（簡易版）
            slug = form.name.data.lower().replace(' ', '-').replace('　', '-')
            
            tag.name = form.name.data
            tag.slug = slug
            db.session.commit()
            flash(f'タグ "{tag.name}" が正常に更新されました。', 'success')
            return redirect(url_for('tags.list_tags'))
        except IntegrityError as e:
            db.session.rollback()
            if 'name_user_id_uc' in str(e):
                flash('このタグ名は既に存在します。', 'danger')
            elif 'slug_user_id_uc' in str(e):
                flash('このスラッグは既に存在します。', 'danger')
            else:
                flash(f'タグの更新中にエラーが発生しました: {e}', 'danger')
            current_app.logger.error(f"IntegrityError updating tag {tag_id}: {e}", exc_info=True)
        except Exception as e:
            db.session.rollback()
            flash(f'タグの更新中にエラーが発生しました: {e}', '危険')
            current_app.logger.error(f"Error updating tag {tag_id}: {e}", exc_info=True)
            
    return render_template('tags/edit_tag.html', form=form, tag=tag, title='タグを編集')

# タグ削除
@tags_bp.route('/tags/delete/<uuid:tag_id>', methods=['POST'])
@login_required
def delete_tag(tag_id):
    tag = db.session.get(Tag, tag_id)
    if tag is None:
        abort(404)

    # 権限チェック（作成者または管理者のみ）
    if tag.user_id != current_user.id and \
       (not hasattr(current_user, 'role') or not current_user.role or current_user.role.name != 'admin'):
        flash('この操作を行う権限がありません。', 'danger')
        current_app.logger.warning(f"ACCESS_DENIED: User {current_user.id} attempted to delete tag {tag_id} without permission.")
        abort(403)

    try:
        # このタグに紐づく投稿からタグの関連付けを削除
        # post_tagsテーブルから該当レコードを削除（多対多関係の解除）
        db.session.execute(post_tags.delete().where(post_tags.c.tag_id == tag.id))
        
        db.session.delete(tag)
        db.session.commit()
        flash('タグが正常に削除されました。関連する投稿からタグの関連付けが解除されました。', 'success')
        current_app.logger.info(f"Tag {tag_id} deleted successfully. Associated posts updated.")
    except Exception as e:
        db.session.rollback()
        flash(f'タグの削除中にエラーが発生しました: {e}', 'danger')
        current_app.logger.error(f"Error deleting tag {tag_id}: {e}", exc_info=True)
    
    return redirect(url_for('tags.list_tags'))