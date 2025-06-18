# F:\dev\BrogDev\app\admin\routes.py

import os
import uuid
import datetime
import qrcode
from io import BytesIO
import base64

from flask import render_template, redirect, url_for, flash, request, current_app, abort, send_from_directory, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, cast, String
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash # パスワードハッシュ化のために追加

from app import db
from app.models import Post, Category, User, Comment, Tag, Image, QR # QRモデルも追加
# 仮のフォームクラス。実際のアプリケーションでは app/forms.py に定義が必要です。
from app.forms import CsrfOnlyForm, PostForm, UserForm, CategoryForm, TagForm, QRForm, ImageUploadForm, ContactForm # 必要に応じて追加


# Blueprintをインポート（__init__.pyでbpとして定義されているものをblog_admin_bpとして利用）
from app.admin import bp as blog_admin_bp

# 役割ベースのアクセス制御デコレータ（app/decorators.py に定義されている前提）
# from app.decorators import roles_required 

# ====================================================================
# ヘルパー関数
# ====================================================================

def allowed_file(filename):
    """許可されたファイル拡張子をチェックするヘルパー関数"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def _save_image(file):
    """画像を保存し、Imageモデルインスタンスを返すヘルパー関数"""
    if file and allowed_file(file.filename):
        # UUIDとオリジナル拡張子を組み合わせたユニークなファイル名を生成
        original_filename = secure_filename(file.filename)
        extension = os.path.splitext(original_filename)[1]
        unique_filename = str(uuid.uuid4()) + extension
        
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)

        # Imageモデルインスタンスを作成
        # url_for('uploaded_file', ...) は、uploaded_fileエンドポイントが定義されている前提
        image_url = url_for('uploaded_file', filename=unique_filename)
        new_image = Image(filename=unique_filename, url=image_url)
        db.session.add(new_image)
        db.session.flush() # IDを生成するためにflush
        return new_image
    return None

# ====================================================================
# 管理ダッシュボード
# ====================================================================
@blog_admin_bp.route('/')
@blog_admin_bp.route('/index')
@login_required 
# @roles_required(['admin', 'editor', 'poster']) 
def admin_dashboard():
    # 統計情報の取得
    total_posts = Post.query.count()
    published_posts = Post.query.filter_by(is_published=True).count()
    draft_posts = Post.query.filter_by(is_published=False).count()
    
    # カテゴリ数を取得（少なくとも1つ以上の投稿に紐づくカテゴリの数を取得）
    actual_category_count = db.session.query(Category.id).join(Post).distinct().count()
    
    # コメント数を取得（未承認コメントも含む）
    total_comments = Comment.query.count()
    unapproved_comments = Comment.query.filter_by(is_approved=False).count()
    
    # 最新の投稿を取得 (例: 最新6件をGistのテンプレートに合わせて表示)
    latest_posts = Post.query.order_by(Post.created_at.desc()).limit(6).all()

    # 投稿をカテゴリごとにグループ化して、ダッシュボードの投稿一覧セクションで利用
    # Gistのindex.htmlの`grouped_posts`に対応
    all_posts = Post.query.order_by(Post.created_at.desc()).all()
    grouped_posts = {}
    if all_posts:
        for post in all_posts:
            category_name = post.category.name if post.category else '未分類'
            if category_name not in grouped_posts:
                grouped_posts[category_name] = []
            grouped_posts[category_name].append(post)

    # テンプレートにデータを渡す
    return render_template('admin/index.html',
                           total_posts=total_posts,
                           published_posts=published_posts,
                           draft_posts=draft_posts,
                           actual_category_count=actual_category_count,
                           total_comments=total_comments,
                           unapproved_comments=unapproved_comments,
                           latest_posts=latest_posts, # Gistのlatest_postsに対応
                           grouped_posts=grouped_posts, # Gistのgrouped_postsに対応
                           form=CsrfOnlyForm() # CSRF保護のためにフォームも渡す
                          )

# ====================================================================
# 投稿管理
# ====================================================================

# 投稿一覧 (Gistのlist_postsをベース)
@blog_admin_bp.route('/posts')
@login_required
# @roles_required(['admin', 'editor', 'poster'])
def list_posts():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('admin/posts/list_posts.html', posts=posts, form=CsrfOnlyForm())

# 新規投稿作成 (Gistのnew_postをベースにフォームと画像処理を改善)
@blog_admin_bp.route('/new_post', methods=['GET', 'POST'])
@login_required
# @roles_required(['admin', 'editor', 'poster'])
def new_post():
    form = PostForm() # app/forms.py に PostForm を定義しておく必要があります
    if form.validate_on_submit():
        main_image = _save_image(form.image_file.data) if form.image_file.data else None

        new_post = Post(
            title=form.title.data,
            body=form.body.data,
            category_id=form.category.data.id if form.category.data else None,
            user_id=current_user.id,
            is_published=form.is_published.data,
            main_image=main_image
        )
        db.session.add(new_post)
        
        # タグの処理
        if form.tags.data:
            tag_names = [tag.strip() for tag in form.tags.data.split(',') if tag.strip()]
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                new_post.tags.append(tag)
        
        db.session.commit()
        flash('新しい投稿が作成されました！', 'success')
        return redirect(url_for('blog_admin_bp.list_posts'))
    
    categories = Category.query.all()
    return render_template('admin/posts/new_post.html', form=form, categories=categories)

# 投稿編集 (Gistのedit_postをベースにフォームと画像処理を改善)
@blog_admin_bp.route('/edit_post/<uuid:post_id>', methods=['GET', 'POST'])
@login_required
# @roles_required(['admin', 'editor', 'poster'])
def edit_post(post_id):
    post = Post.query.get_or_404(str(post_id))

    # 投稿者自身か管理者のみ編集可能
    if not (current_user.id == post.user_id or (current_user.role and current_user.role.name == 'admin')):
        abort(403) # Forbidden

    form = PostForm(obj=post) # PostFormが定義されていることを前提とする

    if request.method == 'GET':
        # 既存のタグをフォームにセット
        form.tags.data = ", ".join([tag.name for tag in post.tags])
    
    if form.validate_on_submit():
        post.title = form.title.data
        post.body = form.body.data
        post.is_published = form.is_published.data
        post.category_id = form.category.data.id if form.category.data else None

        # 画像ファイルの更新ロジック (Gistの既存ロジックと統合)
        if form.image_file.data: # 新しい画像がアップロードされた場合
            # 古い画像があれば削除
            if post.main_image:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], post.main_image.filename))
                    db.session.delete(post.main_image)
                except FileNotFoundError:
                    current_app.logger.warning(f"Old image file not found: {post.main_image.filename}")
            
            # 新しい画像の保存とImageモデルへの登録
            new_image = _save_image(form.image_file.data)
            post.main_image = new_image
        elif form.clear_image.data and post.main_image: # 画像を削除するチェックボックスがある場合
            try:
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], post.main_image.filename))
                db.session.delete(post.main_image)
                post.main_image = None
            except FileNotFoundError:
                current_app.logger.warning(f"Image file to clear not found: {post.main_image.filename}")

        # タグの更新
        post.tags.clear() # 既存のタグをクリア
        if form.tags.data:
            tag_names = [tag.strip() for tag in form.tags.data.split(',') if tag.strip()]
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                post.tags.append(tag)

        db.session.commit()
        flash('投稿が更新されました！', 'success')
        return redirect(url_for('blog_admin_bp.list_posts'))
    
    categories = Category.query.all()
    return render_template('admin/posts/edit_post.html', form=form, post=post, categories=categories)


# 投稿削除 (Gistのdelete_postをベースにCSRF保護と権限チェックを追加)
@blog_admin_bp.route('/delete_post/<uuid:post_id>', methods=['POST'])
@login_required
# @roles_required(['admin', 'editor']) # 管理者または編集者のみ削除可能
def delete_post(post_id):
    form = CsrfOnlyForm() # 削除用のCSRFフォーム
    if form.validate_on_submit():
        post = Post.query.get_or_404(str(post_id))
        
        # 投稿者自身か管理者のみ削除可能
        if not (current_user.id == post.user_id or (current_user.role and current_user.role.name == 'admin')):
            flash('この投稿を削除する権限がありません。', 'danger')
            return redirect(url_for('blog_admin_bp.list_posts'))

        # 関連する画像ファイルを削除（あれば）
        if post.main_image:
            try:
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], post.main_image.filename))
                db.session.delete(post.main_image)
            except FileNotFoundError:
                current_app.logger.warning(f"Image file not found for deletion: {post.main_image.filename}")

        db.session.delete(post)
        db.session.commit()
        flash(f'投稿 "{post.title}" を削除しました。', 'success')
    else:
        flash('無効なリクエストです。', 'error')
    return redirect(url_for('blog_admin_bp.list_posts'))

# 投稿の公開状態切り替え (以前の議論で修正済み、CSRF保護あり)
@blog_admin_bp.route('/toggle_publish/<uuid:post_id>', methods=['POST'])
@login_required
# @roles_required(['admin', 'editor', 'poster'])
def toggle_publish(post_id):
    form = CsrfOnlyForm()
    if form.validate_on_submit():
        post = Post.query.get_or_404(str(post_id))
        post.is_published = not post.is_published
        db.session.commit()
        flash(f'投稿 "{post.title}" の公開状態を切り替えました。', 'success')
    else:
        flash('無効なリクエストです。', 'error')
    return redirect(url_for('blog_admin_bp.list_posts'))

# ====================================================================
# カテゴリ管理
# ====================================================================

# カテゴリ一覧表示と追加/編集/削除 (Gistのmanage_categoriesをベースにCRUD操作を統合)
@blog_admin_bp.route('/manage_categories', methods=['GET', 'POST'])
@login_required
# @roles_required(['admin']) # 管理者のみアクセス可能
def manage_categories():
    form = CategoryForm() # CategoryFormが定義されていることを前提とする

    if request.method == 'POST' and form.validate_on_submit():
        # 追加または編集の処理
        if request.form.get('category_id'): # 隠しフィールドでIDが送られてきたら編集
            category_id = int(request.form.get('category_id'))
            category = Category.query.get_or_404(category_id)
            category.name = form.name.data
            flash('カテゴリが更新されました！', 'success')
        else: # IDがなければ新規追加
            new_category = Category(name=form.name.data)
            db.session.add(new_category)
            flash('新しいカテゴリが追加されました！', 'success')
        db.session.commit()
        return redirect(url_for('blog_admin_bp.manage_categories'))
    
    categories = Category.query.order_by(Category.name).all()
    # GistのHTMLに合わせて、カテゴリ編集用のデータも渡す必要があれば調整
    return render_template('admin/categories/manage_categories.html', categories=categories, form=form, CsrfOnlyForm=CsrfOnlyForm)

# カテゴリ削除 (POSTリクエストで受け付ける)
@blog_admin_bp.route('/delete_category/<int:category_id>', methods=['POST'])
@login_required
# @roles_required(['admin'])
def delete_category(category_id):
    form = CsrfOnlyForm() # CSRF保護
    if form.validate_on_submit():
        category = Category.query.get_or_404(category_id)
        
        # このカテゴリに紐づく投稿がある場合、それらのカテゴリを「未分類」に移動
        if category.posts:
            uncategorized = Category.query.filter_by(name='未分類').first()
            if not uncategorized:
                uncategorized = Category(name='未分類')
                db.session.add(uncategorized)
                db.session.commit() # 未分類カテゴリを先にコミット

            for post in category.posts:
                post.category = uncategorized
            db.session.commit()
            flash(f'カテゴリ "{category.name}" に紐づく投稿は未分類に移動されました。', 'info')
        
        db.session.delete(category)
        db.session.commit()
        flash(f'カテゴリ "{category.name}" を削除しました。', 'success')
    else:
        flash('無効なリクエストです。', 'error')
    return redirect(url_for('blog_admin_bp.manage_categories'))


# ====================================================================
# コメント管理
# ====================================================================

# コメント一覧 (Gistのlist_commentsをベース)
@blog_admin_bp.route('/list_comments', methods=['GET', 'POST']) # 承認/削除がPOSTで来る可能性を考慮
@login_required
# @roles_required(['admin', 'editor'])
def list_comments():
    comments = Comment.query.order_by(Comment.created_at.desc()).all()
    # コメントの承認・削除用のフォーム
    return render_template('admin/comments/list_comments.html', comments=comments, form=CsrfOnlyForm())

# コメントの承認/非承認切り替え (CSRF保護あり)
@blog_admin_bp.route('/comment/<uuid:comment_id>/toggle_approval', methods=['POST'])
@login_required
# @roles_required(['admin', 'editor'])
def toggle_comment_approval(comment_id):
    form = CsrfOnlyForm()
    if form.validate_on_submit():
        comment = Comment.query.get_or_404(str(comment_id))
        comment.is_approved = not comment.is_approved
        db.session.commit()
        flash(f'コメントの承認状態を切り替えました。', 'success')
    else:
        flash('無効なリクエストです。', 'error')
    return redirect(url_for('blog_admin_bp.list_comments'))

# コメント削除 (CSRF保護あり)
@blog_admin_bp.route('/delete_comment/<uuid:comment_id>', methods=['POST'])
@login_required
# @roles_required(['admin'])
def delete_comment(comment_id):
    form = CsrfOnlyForm()
    if form.validate_on_submit():
        comment = Comment.query.get_or_404(str(comment_id))
        db.session.delete(comment)
        db.session.commit()
        flash('コメントを削除しました。', 'success')
    else:
        flash('無効なリクエストです。', 'error')
    return redirect(url_for('blog_admin_bp.list_comments'))

# ====================================================================
# タグ管理
# ====================================================================

# タグ一覧と追加/編集/削除 (Gistにはないが、管理画面に必要)
@blog_admin_bp.route('/tags', methods=['GET', 'POST'])
@login_required
# @roles_required(['admin', 'editor'])
def list_tags():
    form = TagForm() # app/forms.py に TagForm を定義しておく必要があります
    if form.validate_on_submit():
        # タグの追加または編集処理
        tag_id = request.form.get('tag_id') # 編集の場合にIDを取得
        if tag_id:
            tag = Tag.query.get_or_404(int(tag_id))
            tag.name = form.name.data
            flash('タグが更新されました！', 'success')
        else:
            new_tag = Tag(name=form.name.data)
            db.session.add(new_tag)
            flash('新しいタグが追加されました！', 'success')
        db.session.commit()
        return redirect(url_for('blog_admin_bp.list_tags'))

    tags = Tag.query.order_by(Tag.name).all()
    return render_template('admin/tags/manage_tags.html', tags=tags, form=form, CsrfOnlyForm=CsrfOnlyForm)

# タグ削除 (POSTリクエストで受け付ける)
@blog_admin_bp.route('/delete_tag/<int:tag_id>', methods=['POST'])
@login_required
# @roles_required(['admin'])
def delete_tag(tag_id):
    form = CsrfOnlyForm()
    if form.validate_on_submit():
        tag = Tag.query.get_or_404(tag_id)
        # タグが投稿に紐づいている場合、紐付けを解除
        for post in tag.posts:
            post.tags.remove(tag)
        db.session.delete(tag)
        db.session.commit()
        flash(f'タグ "{tag.name}" を削除しました。', 'success')
    else:
        flash('無効なリクエストです。', 'error')
    return redirect(url_for('blog_admin_bp.list_tags'))

# ====================================================================
# ユーザー管理
# ====================================================================

# ユーザー管理 (Gistのuser_managementをベース)
@blog_admin_bp.route('/user_management')
@login_required
# @roles_required(['admin']) # 管理者のみアクセス可能
def user_management():
    users = User.query.all()
    return render_template('admin/user_management.html', users=users, form=CsrfOnlyForm())

# ユーザー編集 (Gistのedit_userをベース)
@blog_admin_bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
# @roles_required(['admin'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user) # UserFormが定義されていることを前提とする

    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        # パスワードはフォームで入力された場合のみ更新
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)
        user.is_active = form.is_active.data
        user.role_id = form.role.data.id if form.role.data else None # ロールIDの更新

        db.session.commit()
        flash('ユーザー情報が更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.user_management'))
    
    return render_template('admin/edit_user.html', form=form, user=user)

# ユーザーのアクティブ状態切り替え (Gistのtoggle_user_activeをベースにCSRF保護追加)
@blog_admin_bp.route('/toggle_user_active/<int:user_id>', methods=['POST'])
@login_required
# @roles_required(['admin'])
def toggle_user_active(user_id):
    form = CsrfOnlyForm()
    if form.validate_on_submit():
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            flash('自分自身のアクティブ状態を切り替えることはできません。', 'danger')
        else:
            user.is_active = not user.is_active
            db.session.commit()
            flash(f'ユーザー {user.username} のアクティブ状態を切り替えました。', 'success')
    else:
        flash('無効なリクエストです。', 'error')
    return redirect(url_for('blog_admin_bp.user_management'))

# ユーザー削除 (Gistのdelete_userをベースにCSRF保護追加)
@blog_admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
# @roles_required(['admin'])
def delete_user(user_id):
    form = CsrfOnlyForm()
    if form.validate_on_submit():
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            flash('自分自身を削除することはできません。', 'danger')
        else:
            # ユーザーに関連する投稿、コメントなどをどうするか検討
            # 例えば、投稿のuser_idをNoneにする、または削除するなど
            # 簡単化のため、ここでは関連する投稿やコメントはそのまま残ると仮定（CASCADE設定による）
            db.session.delete(user)
            db.session.commit()
            flash(f'ユーザー {user.username} を削除しました。', 'success')
    else:
        flash('無効なリクエストです。', 'error')
    return redirect(url_for('blog_admin_bp.user_management'))

# ====================================================================
# 画像管理
# ====================================================================

# 画像管理 (Gistのimage_managementをベースにアップロード処理を統合)
@blog_admin_bp.route('/image_management', methods=['GET', 'POST'])
@login_required
# @roles_required(['admin', 'editor', 'poster'])
def image_management():
    form = ImageUploadForm() # 画像アップロードフォーム (app/forms.pyに定義)
    if form.validate_on_submit():
        new_image = _save_image(form.image_file.data)
        if new_image:
            db.session.commit()
            flash('画像が正常にアップロードされました。', 'success')
        else:
            flash('画像のアップロードに失敗しました。許可されていないファイル形式かもしれません。', 'error')
        return redirect(url_for('blog_admin_bp.image_management'))

    images = Image.query.order_by(Image.uploaded_at.desc()).all()
    return render_template('admin/image_management.html', images=images, form=form, CsrfOnlyForm=CsrfOnlyForm)

# 画像削除 (CSRF保護あり)
@blog_admin_bp.route('/delete_image/<uuid:image_id>', methods=['POST'])
@login_required
# @roles_required(['admin', 'editor'])
def delete_image(image_id):
    form = CsrfOnlyForm()
    if form.validate_on_submit():
        image = Image.query.get_or_404(str(image_id))
        
        # 物理ファイルの削除
        try:
            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], image.filename))
        except FileNotFoundError:
            current_app.logger.warning(f"Image file not found for deletion: {image.filename}")
        
        db.session.delete(image)
        db.session.commit()
        flash('画像を削除しました。', 'success')
    else:
        flash('無効なリクエストです。', 'error')
    return redirect(url_for('blog_admin_bp.image_management'))

# ====================================================================
# QRコード管理
# ====================================================================

# QRコード一覧と作成 (Gistのqr_code_managementをベース)
@blog_admin_bp.route('/qr_code_management', methods=['GET', 'POST'])
@login_required
# @roles_required(['admin'])
def qr_code_management():
    form = QRForm() # QRFormが定義されていることを前提とする

    if form.validate_on_submit():
        url = form.url.data
        qr_filename = f"qr_{uuid.uuid4()}.png"
        qr_filepath = os.path.join(current_app.root_path, 'static', 'qrcodes', qr_filename) # static/qrcodesに保存

        # QRコード生成
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(qr_filepath), exist_ok=True)
        img.save(qr_filepath)

        new_qr = QR(
            name=form.name.data,
            url=url,
            qr_image_filename=qr_filename
        )
        db.session.add(new_qr)
        db.session.commit()
        flash('QRコードが正常に作成されました。', 'success')
        return redirect(url_for('blog_admin_bp.qr_code_management'))

    qrs = QR.query.all()
    return render_template('admin/qr_code_management.html', qrs=qrs, form=form, CsrfOnlyForm=CsrfOnlyForm)

# QRコード削除 (CSRF保護あり)
@blog_admin_bp.route('/delete_qr/<int:qr_id>', methods=['POST'])
@login_required
# @roles_required(['admin'])
def delete_qr(qr_id):
    form = CsrfOnlyForm()
    if form.validate_on_submit():
        qr_code = QR.query.get_or_404(qr_id)
        
        # 物理ファイルを削除
        qr_filepath = os.path.join(current_app.root_path, 'static', 'qrcodes', qr_code.qr_image_filename)
        try:
            os.remove(qr_filepath)
        except FileNotFoundError:
            current_app.logger.warning(f"QR code image file not found for deletion: {qr_filepath}")
        
        db.session.delete(qr_code)
        db.session.commit()
        flash('QRコードを削除しました。', 'success')
    else:
        flash('無効なリクエストです。', 'error')
    return redirect(url_for('blog_admin_bp.qr_code_management'))


# ====================================================================
# 一般設定 (Gistのsettingsをベース)
# ====================================================================
@blog_admin_bp.route('/settings')
@login_required
# @roles_required(['admin']) # 管理者のみアクセス可能
def settings():
    # ここに設定情報をロードするロジック
    # 例: general_settings = load_settings_from_db()
    flash('設定管理機能は未実装です。', 'info')
    return render_template('admin/settings.html')


# ====================================================================
# お問い合わせ管理 (Gistのcontact_messagesをベース)
# ====================================================================

# お問い合わせメッセージ一覧 (Gistのcontact_messagesをベース)
@blog_admin_bp.route('/contact_messages')
@login_required
# @roles_required(['admin', 'editor'])
def contact_messages():
    # 仮のメッセージリスト。実際にはデータベースから取得
    # messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    messages = [] # 仮に空リスト
    flash('お問い合わせメッセージ管理機能は未実装です。', 'info')
    return render_template('admin/contact_messages.html', messages=messages)

# お問い合わせメッセージ詳細 (Gistのcontact_message_detailをベース)
@blog_admin_bp.route('/contact_message/<int:message_id>')
@login_required
# @roles_required(['admin', 'editor'])
def contact_message_detail(message_id):
    # message = ContactMessage.query.get_or_404(message_id)
    message = None # 仮にNone
    flash(f'お問い合わせメッセージ ID: {message_id} の詳細機能は未実装です。', 'info')
    return render_template('admin/contact_message_detail.html', message=message)

# お問い合わせメッセージ削除 (Gistのdelete_contact_messageをベースにCSRF保護追加)
@blog_admin_bp.route('/delete_contact_message/<int:message_id>', methods=['POST'])
@login_required
# @roles_required(['admin'])
def delete_contact_message(message_id):
    form = CsrfOnlyForm()
    if form.validate_on_submit():
        # message = ContactMessage.query.get_or_404(message_id)
        # db.session.delete(message)
        # db.session.commit()
        flash('お問い合わせメッセージを削除しました。（機能は未実装）', 'success')
    else:
        flash('無効なリクエストです。', 'error')
    return redirect(url_for('blog_admin_bp.contact_messages'))

# ====================================================================
# ファイルとメディア
# ====================================================================

# 一括アップロードフォームの表示 (Gistのshow_bulk_upload_formをベース)
# ※ 実際のアップロード処理は別途実装が必要です。これはフォーム表示のみ。
@blog_admin_bp.route('/bulk_upload_form')
@login_required
# @roles_required(['admin', 'editor', 'poster'])
def show_bulk_upload_form():
    flash('一括アップロードフォーム機能は未実装です。', 'info')
    return render_template('admin/bulk_upload_form.html', form=CsrfOnlyForm())

# アップロードされたファイルを提供するエンドポイント (Gistのuploaded_fileをベース)
# これはBluePrintの外、アプリケーションのルートに定義されることが多いですが、
# Gistの構造に合わせてここに仮で配置します。必要に応じて app/__init__.py などに移動してください。
@blog_admin_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

# ====================================================================
# APIエンドポイント (Gistのget_post_data, update_post_statusをベース)
# ====================================================================

# 単一投稿のデータを取得するAPIエンドポイント
@blog_admin_bp.route('/api/posts/<uuid:post_id>', methods=['GET'])
@login_required
def get_post_data(post_id):
    post = Post.query.get(str(post_id))
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    # 投稿オブジェクトを辞書に変換してJSONで返す (必要に応じて詳細化)
    return jsonify({
        'id': post.id,
        'title': post.title,
        'body': post.body,
        'is_published': post.is_published,
        'created_at': post.created_at.isoformat(),
        'updated_at': post.updated_at.isoformat() if post.updated_at else None,
        'category': post.category.name if post.category else '未分類',
        'tags': [tag.name for tag in post.tags],
        'main_image_url': post.main_image.url if post.main_image else None
    })

# 投稿のステータス（公開/下書き）を更新するAPIエンドポイント (Gistのupdate_post_statusをベース)
@blog_admin_bp.route('/api/posts/<uuid:post_id>/status', methods=['PUT'])
@login_required
# @roles_required(['admin', 'editor', 'poster']) # APIも権限で保護
def update_post_status(post_id):
    data = request.get_json()
    if not data or 'is_published' not in data:
        return jsonify({'error': 'Invalid request data'}), 400

    post = Post.query.get(str(post_id))
    if not post:
        return jsonify({'error': 'Post not found'}), 404

    # 投稿者自身か管理者のみ更新可能
    if not (current_user.id == post.user_id or (current_user.role and current_user.role.name == 'admin')):
        return jsonify({'error': 'Permission denied'}), 403

    post.is_published = data['is_published']
    db.session.commit()
    return jsonify({'message': 'Post status updated successfully', 'is_published': post.is_published})

# ====================================================================
# その他 (Gistのその他の部分)
# ====================================================================

# ファイルのアップロードと表示 (Gistのupload_fileをベース、image_managementと重複する可能性あり)
@blog_admin_bp.route('/upload_file', methods=['GET', 'POST'])
@login_required
# @roles_required(['admin', 'editor', 'poster'])
def upload_file():
    form = ImageUploadForm() # ImageUploadFormを使用
    if form.validate_on_submit():
        new_image = _save_image(form.image_file.data)
        if new_image:
            db.session.commit()
            flash('ファイルが正常にアップロードされました。', 'success')
            return redirect(url_for('blog_admin_bp.uploaded_file', filename=new_image.filename)) # uploaded_fileへリダイレクト
        else:
            flash('ファイルのアップロードに失敗しました。', 'error')
    return render_template('admin/upload_file.html', form=form) # upload_file.htmlテンプレートが必要


# ====================================================================
# エラーハンドリング (Gistにはないが、追加)
# ====================================================================
@blog_admin_bp.app_errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

@blog_admin_bp.app_errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@blog_admin_bp.app_errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500