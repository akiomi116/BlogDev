# F:\dev\BrogDev\app\admin\routes.py

import os
import uuid
from flask import render_template, url_for, flash, redirect, request, current_app, Blueprint, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func
from PIL import Image as PilImage

from app.extensions import db
from app.models import User, Role, Post, Category, Tag, Image, Comment

# app/forms.py から汎用フォームをインポート
from app.forms import CsrfOnlyForm 

# app/admin/forms.py から管理画面専用フォームをインポート
from app.admin.forms import (
    UserForm, RoleForm, DeleteRoleForm, UserRoleForm, # UserRoleForm も追加
    PostForm, CategoryForm, TagForm,
    ImageUploadForm, BulkImageUploadForm,
    AdminCommentForm, # ← CommentForm から AdminCommentForm に変更
    QRForm # もし管理画面でQRFormを使うなら追加
)

from app.decorators import roles_required

from slugify import slugify

from . import bp

# 定数
THUMBNAIL_SIZE = (200, 200) # サムネイルのサイズを定義

# 許可されるファイル拡張子
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# --- ダッシュボード ---
@bp.route('/')
@bp.route('/index')
@login_required
@roles_required(['admin', 'editor', 'poster']) # 適切なロールを設定
def index():
    # ユーザーが'admin'ロールを持っているか確認
    if current_user.has_role('admin'):
        total_users = User.query.count()
        total_posts = Post.query.count()
        total_categories = Category.query.count()
        total_tags = Tag.query.count()
        total_images = Image.query.count()
        total_comments = Comment.query.count()
        pending_comments_count = Comment.query.filter_by(is_approved=False).count()

        # 最近の活動 (例: 最新の投稿とコメント)
        latest_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
        latest_comments = Comment.query.order_by(Comment.created_at.desc()).limit(5).all()

        return render_template('index.html', # 'admin/index.html' -> 'index.html'
                               total_users=total_users,
                               total_posts=total_posts,
                               total_categories=total_categories,
                               total_tags=total_tags,
                               total_images=total_images,
                               total_comments=total_comments,
                               pending_comments_count=pending_comments_count,
                               latest_posts=latest_posts,
                               latest_comments=latest_comments,
                               title='管理ダッシュボード')
    else:
        # 'admin'ロールを持たないユーザー向けのダッシュボード（簡略版など）
        # 例えば、自分の投稿のみを表示するなど
        user_posts_count = Post.query.filter_by(user_id=current_user.id).count()
        user_comments_count = Comment.query.filter_by(user_id=current_user.id).count()
        
        latest_user_posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.created_at.desc()).limit(5).all()

        return render_template('dashboard.html', # 'admin/dashboard.html' -> 'dashboard.html'
                               user_posts_count=user_posts_count,
                               user_comments_count=user_comments_count,
                               latest_user_posts=latest_user_posts,
                               title='ユーザーダッシュボード')

# --- ユーザー管理 ---
@bp.route('/users')
@login_required
@roles_required(['admin'])
def list_users():
    users = User.query.all()
    users_with_roles = []
    for user in users:
        users_with_roles.append({
            'user': user,
            'role_name': user.role.name if user.role else '未設定'
        })
    
    # NameErrorを解消するため、formをインスタンス化
    # list_users.htmlで新規ユーザー作成フォームとして使うことを想定
    form = UserForm()
    # ロールの選択肢を設定
    form.role_id.choices = [(str(role.id), role.name) for role in Role.query.order_by(Role.name.asc()).all()]

    return render_template('users/list_users.html', users=users_with_roles, form=form, title='ユーザー管理')

@bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def add_user():
    form = UserForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        
        # ロールを設定 (role_id を使用)
        role = Role.query.get(form.role_id.data)
        if role:
            user.role = role
        
        # is_active フィールドの値を設定
        if hasattr(form, 'is_active'):
            user.is_active = form.is_active.data

        db.session.add(user)
        db.session.commit()
        flash('ユーザーが追加されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_users'))
    return render_template('users/add_edit_user.html', form=form, title='ユーザー追加', is_edit=False) # 'admin/users/add_edit_user.html' -> 'users/add_edit_user.html'

@bp.route('/users/edit/<uuid:user_id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def edit_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        flash('ユーザーが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_users'))

    form = UserForm(obj=user)
    # フォームにユーザーの現在のロールIDを初期値として設定
    if user.role:
        form.role_id.data = str(user.role.id)
    else:
        form.role_id.data = '' # ロールが設定されていない場合

    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        if form.password.data:
            user.set_password(form.password.data)
        
        # ロールを設定 (role_id を使用)
        role = Role.query.get(form.role_id.data)
        if role:
            user.role = role
        else:
            user.role = None # ロールが選択されていない場合

        # is_active フィールドの値を設定
        if hasattr(form, 'is_active'):
            user.is_active = form.is_active.data

        db.session.commit()
        flash('ユーザーが更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_users'))
    elif request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        # is_active フィールドの初期値を設定
        if hasattr(form, 'is_active') and hasattr(user, 'is_active'):
            form.is_active.data = user.is_active

    return render_template('users/add_edit_user.html', form=form, user=user, title='ユーザー編集', is_edit=True) # 'admin/users/add_edit_user.html' -> 'users/add_edit_user.html'

@bp.route('/users/delete/<uuid:user_id>', methods=['POST'])
@login_required
@roles_required(['admin'])
def delete_user(user_id):
    user_to_delete = db.session.get(User, user_id)
    if not user_to_delete:
        flash('ユーザーが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_users'))

    # ログイン中のユーザー自身を削除しようとしていないか確認
    if user_to_delete.id == current_user.id:
        flash('自分自身のアカウントを削除することはできません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_users'))

    try:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash('ユーザーが削除されました。', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'ユーザーの削除中にエラーが発生しました: {e}', 'danger')

    return redirect(url_for('blog_admin_bp.list_users'))

# --- ロール管理 ---
@bp.route('/roles')
@login_required
@roles_required(['admin'])
def manage_roles():
    roles = Role.query.all()
    delete_form = DeleteRoleForm() # 削除フォームを各ロール用にインスタンス化
    return render_template('roles/manage_roles.html', roles=roles, delete_form=delete_form, title='ロール管理') # 'admin/roles/manage_roles.html' -> 'roles/manage_roles.html'

@bp.route('/roles/add', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def add_role():
    form = RoleForm()
    if form.validate_on_submit():
        role = Role(name=form.name.data)
        db.session.add(role)
        db.session.commit()
        flash('新しいロールが追加されました。', 'success')
        return redirect(url_for('blog_admin_bp.manage_roles'))
    return render_template('roles/add_edit_role.html', form=form, title='ロール追加', is_edit=False) # 'admin/roles/add_edit_role.html' -> 'roles/add_edit_role.html'

@bp.route('/roles/edit/<int:role_id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def edit_role(role_id):
    role = db.session.get(Role, role_id)
    if role is None:
        flash('ロールが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.manage_roles'))

    form = RoleForm(obj=role)
    if form.validate_on_submit():
        role.name = form.name.data
        db.session.commit()
        flash('ロールが更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.manage_roles'))
    elif request.method == 'GET':
        form.name.data = role.name
    return render_template('roles/add_edit_role.html', form=form, role=role, title='ロール編集', is_edit=True) # 'admin/roles/add_edit_role.html' -> 'roles/add_edit_role.html'

@bp.route('/roles/delete/<int:role_id>', methods=['POST'])
@login_required
@roles_required(['admin'])
def delete_role(role_id):
    role_to_delete = db.session.get(Role, role_id)
    if not role_to_delete:
        flash('ロールが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.manage_roles'))

    # 'admin'ロールは削除できないようにする
    if role_to_delete.name == 'admin':
        flash('「admin」ロールは削除できません。', 'danger')
        return redirect(url_for('blog_admin_bp.manage_roles'))

    # そのロールに属するユーザーがいないか確認
    # ロールに紐づくユーザーがいる場合、先にユーザーのロールを解除または変更する必要がある
    if role_to_delete.users.count() > 0:
        flash(f'このロールにはまだ{role_to_delete.users.count()}人のユーザーが紐付いています。先にこれらのユーザーのロールを変更または削除してください。', 'warning')
        return redirect(url_for('blog_admin_bp.manage_roles'))

    try:
        db.session.delete(role_to_delete)
        db.session.commit()
        flash('ロールが削除されました。', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'ロールの削除中にエラーが発生しました: {e}', 'danger')

    return redirect(url_for('blog_admin_bp.manage_roles'))

# --- 投稿管理 ---
@bp.route('/posts')
@login_required
@roles_required(['admin', 'editor', 'poster'])
def list_posts():
    if current_user.has_role('admin'):
        posts = Post.query.order_by(Post.created_at.desc()).all()
    else:
        posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.created_at.desc()).all()
    
    # CSRF保護のためのフォームを渡す
    csrf_form = CsrfOnlyForm() 

    return render_template('posts/list_posts.html', posts=posts, title='投稿管理', csrf_form=csrf_form)

@bp.route('/posts/new', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'editor', 'poster'])
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        main_image_file = form.main_image_file.data
        selected_main_image_id = form.main_image.data
        
        main_image_obj = None
        if main_image_file and allowed_file(main_image_file.filename):
            # 新しいメイン画像をアップロード
            unique_filename = str(uuid.uuid4()) + os.path.splitext(secure_filename(main_image_file.filename))[1]
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'images', unique_filename)
            main_image_file.save(filepath)

            # サムネイル生成
            thumbnail_filename = 'thumb_' + unique_filename
            thumbnail_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'thumbnails', thumbnail_filename)
            PilImage.open(filepath).thumbnail(THUMBNAIL_SIZE).save(thumbnail_filepath)
            
            main_image_obj = Image(
                original_filename=main_image_file.filename,
                unique_filename=unique_filename,
                thumbnail_filename=thumbnail_filename,
                filepath=f'uploads/images/{unique_filename}',
                thumbnail_filepath=f'uploads/thumbnails/{thumbnail_filename}',
                user_id=current_user.id,
                is_main_image=True,
                alt_text=form.main_image_alt_text.data # 修正: PostForm に追加した main_image_alt_text を使用
            )
            db.session.add(main_image_obj)
            db.session.flush() # IDを生成するためにflush
        elif selected_main_image_id:
            # 既存のメイン画像を選択
            main_image_obj = db.session.get(Image, selected_main_image_id)
            if main_image_obj:
                # 既存の画像をメイン画像として使用する場合、元のis_main_imageをFalseに設定するロジックが必要な場合がある
                # ただし、main_image_idがunique=Trueなので、自動的に更新されるはず
                main_image_obj.is_main_image = True # 明示的にTrueに設定
                if form.main_image_alt_text.data: # 修正: PostForm に追加した main_image_alt_text を使用
                    main_image_obj.alt_text = form.main_image_alt_text.data
            else:
                flash('選択されたメイン画像が見つかりません。', 'warning')
                return redirect(url_for('blog_admin_bp.new_post'))
        
        category = None
        if form.category.data:
            category = db.session.get(Category, form.category.data)

        new_post = Post(
            title=form.title.data,
            body=form.body.data,
            posted_by=current_user,
            category=category,
            is_published=form.is_published.data,
            main_image=main_image_obj # メイン画像オブジェクトを割り当て
        )
        db.session.add(new_post)
        db.session.flush() # new_post.id を生成するためにflush

        # タグの関連付け
        selected_tags = []
        if form.tags.data:
            selected_tags = Tag.query.filter(Tag.id.in_(form.tags.data)).all()
        new_post.tags = selected_tags

        # 追加画像の関連付け
        selected_additional_images = []
        if form.additional_images.data:
            selected_additional_images = Image.query.filter(Image.id.in_(form.additional_images.data)).all()
        new_post.additional_images = selected_additional_images

        db.session.commit()
        flash('新しい投稿が作成されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_posts'))
    
    # GETリクエスト時、またはバリデーションエラー時
    return render_template('posts/edit_post.html', form=form, title='新規投稿', is_edit=False) 

@bp.route('/posts/edit/<uuid:post_id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'editor', 'poster'])
def edit_post(post_id):
    post = db.session.get(Post, post_id)
    if post is None:
        flash('投稿が見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_posts'))

    # 投稿の所有者または管理者のみが編集可能
    if not (current_user.has_role('admin') or post.user_id == current_user.id):
        flash('この投稿を編集する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_posts'))

    form = PostForm(obj=post)

    # フォームの初期値を設定
    if request.method == 'GET':
        form.title.data = post.title
        form.body.data = post.body
        form.is_published.data = post.is_published
        if post.category:
            form.category.data = str(post.category.id)
        form.tags.data = [str(tag.id) for tag in post.tags]
        if post.main_image:
            form.main_image.data = str(post.main_image.id)
            form.main_image_alt_text.data = post.main_image.alt_text # 既存のalt_textをフォームにセット
        form.additional_images.data = [str(img.id) for img in post.additional_images]

    if form.validate_on_submit():
        post.title = form.title.data
        post.body = form.body.data
        post.is_published = form.is_published.data

        # カテゴリの更新
        if form.category.data:
            post.category = db.session.get(Category, form.category.data)
        else:
            post.category = None

        # タグの更新
        selected_tags = []
        if form.tags.data:
            selected_tags = Tag.query.filter(Tag.id.in_(form.tags.data)).all()
        post.tags = selected_tags # 既存のタグを更新

        # メイン画像の処理
        new_main_image_file = form.main_image_file.data
        selected_main_image_id = form.main_image.data

        if new_main_image_file and allowed_file(new_main_image_file.filename):
            # 新しいメイン画像をアップロード
            unique_filename = str(uuid.uuid4()) + os.path.splitext(secure_filename(new_main_image_file.filename))[1]
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'images', unique_filename)
            new_main_image_file.save(filepath)

            # サムネイル生成
            thumbnail_filename = 'thumb_' + unique_filename
            thumbnail_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'thumbnails', thumbnail_filename)
            PilImage.open(filepath).thumbnail(THUMBNAIL_SIZE).save(thumbnail_filepath)
            
            # 古いメイン画像があれば is_main_image を False にする
            if post.main_image:
                post.main_image.is_main_image = False
            
            main_image_obj = Image(
                original_filename=new_main_image_file.filename,
                unique_filename=unique_filename,
                thumbnail_filename=thumbnail_filename,
                filepath=f'uploads/images/{unique_filename}',
                thumbnail_filepath=f'uploads/thumbnails/{thumbnail_filename}',
                user_id=current_user.id,
                is_main_image=True,
                alt_text=form.main_image_alt_text.data # 修正: PostForm に追加した main_image_alt_text を使用
            )
            db.session.add(main_image_obj)
            post.main_image = main_image_obj

        elif selected_main_image_id:
            # 既存のメイン画像を選択
            new_main_image_obj = db.session.get(Image, selected_main_image_id)
            if new_main_image_obj:
                # 既存の画像をメイン画像として使用する場合、元のis_main_imageをFalseに設定するロジックが必要な場合がある
                if post.main_image and post.main_image.id != new_main_image_obj.id:
                    post.main_image.is_main_image = False
                new_main_image_obj.is_main_image = True # 明示的にTrueに設定
                post.main_image = new_main_image_obj
                if form.main_image_alt_text.data: # 修正: PostForm に追加した main_image_alt_text を使用
                    post.main_image.alt_text = form.main_image_alt_text.data
            else:
                # 選択された既存画像が見つからない場合、メイン画像を解除
                if post.main_image:
                    post.main_image.is_main_image = False
                post.main_image = None
                flash('選択されたメイン画像が見つかりません。メイン画像を解除しました。', 'warning')
        else:
            # どちらも選択されていない場合、メイン画像を解除
            if post.main_image:
                post.main_image.is_main_image = False
            post.main_image = None

        # 追加画像の更新
        selected_additional_images = []
        if form.additional_images.data:
            selected_additional_images = Image.query.filter(Image.id.in_(form.additional_images.data)).all()
        post.additional_images = selected_additional_images

        db.session.commit()
        flash('投稿が更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_posts'))

    return render_template('posts/edit_post.html', form=form, post=post, title='投稿編集', is_edit=True) 

@bp.route('/posts/delete/<uuid:post_id>', methods=['POST'])
@login_required
@roles_required(['admin', 'editor', 'poster'])
def delete_post(post_id):
    post_to_delete = db.session.get(Post, post_id)
    if not post_to_delete:
        flash('投稿が見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_posts'))

    # 投稿の所有者または管理者のみが削除可能
    if not (current_user.has_role('admin') or post_to_delete.user_id == current_user.id):
        flash('この投稿を削除する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_posts'))
    try:
        # 関連する画像 (main_imageとadditional_images) の is_main_image フラグを適切に処理
        # cascade='all, delete-orphan' により、関連するコメントは自動的に削除される
        # 画像については、Postに紐づいているImageレコードは削除されるが、
        # 物理ファイルは別途処理する必要がある（ここでは省略）

        db.session.delete(post_to_delete) 
        db.session.commit()
        flash('投稿が削除されました。', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'投稿の削除中にエラーが発生しました: {e}', 'danger')

    return redirect(url_for('blog_admin_bp.list_posts'))

# 新しいルート: 投稿の公開/非公開を切り替える
@bp.route('/posts/toggle_publish/<uuid:post_id>', methods=['POST'])
@login_required
@roles_required(['admin', 'editor', 'poster'])
def toggle_publish(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        flash('投稿が見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_posts'))

    if post.user_id != current_user.id and not current_user.has_role('admin'):
        flash('この投稿の公開状態を変更する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_posts'))

    post.is_published = not post.is_published
    db.session.commit()
    flash(f"投稿 '{post.title}' の公開状態が{'公開' if post.is_published else '非公開'}に切り替わりました。", 'success')
    return redirect(url_for('blog_admin_bp.list_posts'))

# --- カテゴリ管理 ---
@bp.route('/categories')
@login_required
@roles_required(['admin', 'editor', 'poster'])
def list_categories():
    if current_user.has_role('admin'):
        categories = Category.query.order_by(Category.name.asc()).all()
    else:
        # admin 以外のユーザーは自分のカテゴリのみ表示
        categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name.asc()).all()
    return render_template('categories/list_categories.html', categories=categories, title='カテゴリ管理') # 'admin/categories/list_categories.html' -> 'categories/list_categories.html'

@bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'editor', 'poster'])
def add_category():
    form = CategoryForm()
    if form.validate_on_submit():
        slug = slugify(form.slug.data) if form.slug.data else slugify(form.name.data)
        category = Category(name=form.name.data, slug=slug, description=form.description.data, user_id=current_user.id)
        db.session.add(category)
        db.session.commit()
        flash('新しいカテゴリが追加されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_categories'))
    return render_template('categories/add_edit_category.html', form=form, title='カテゴリ追加', is_edit=False) # 'admin/categories/add_edit_category.html' -> 'categories/add_edit_category.html'

@bp.route('/categories/edit/<uuid:category_id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'editor', 'poster'])
def edit_category(category_id):
    category = db.session.get(Category, category_id)
    if category is None:
        flash('カテゴリが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_categories'))
    
    # カテゴリの所有者または管理者のみが編集可能
    if not (current_user.has_role('admin') or category.user_id == current_user.id):
        flash('このカテゴリを編集する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_categories'))

    form = CategoryForm(obj=category)
    if form.validate_on_submit():
        category.name = form.name.data
        category.slug = slugify(form.slug.data) if form.slug.data else slugify(form.name.data)
        category.description = form.description.data
        db.session.commit()
        flash('カテゴリが更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_categories'))
    elif request.method == 'GET':
        form.name.data = category.name
        form.slug.data = category.slug
        form.description.data = category.description
    return render_template('categories/add_edit_category.html', form=form, category=category, title='カテゴリ編集', is_edit=True) # 'admin/categories/add_edit_category.html' -> 'categories/add_edit_category.html'

@bp.route('/categories/delete/<uuid:category_id>', methods=['POST'])
@login_required
@roles_required(['admin', 'editor', 'poster'])
def delete_category(category_id):
    category_to_delete = db.session.get(Category, category_id)
    if not category_to_delete:
        flash('カテゴリが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_categories'))

    # カテゴリの所有者または管理者のみが削除可能
    if not (current_user.has_role('admin') or category_to_delete.user_id == current_user.id):
        flash('このカテゴリを削除する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_categories'))

    if category_to_delete.posts.count() > 0:
        flash(f'このカテゴリにはまだ{category_to_delete.posts.count()}件の投稿が紐付いています。先にこれらの投稿のカテゴリを解除または変更してください。', 'warning')
        return redirect(url_for('blog_admin_bp.list_categories'))

    try:
        db.session.delete(category_to_delete)
        db.session.commit()
        flash('カテゴリが削除されました。', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'カテゴリの削除中にエラーが発生しました: {e}', 'danger')

    return redirect(url_for('blog_admin_bp.list_categories'))


# --- タグ管理 ---
@bp.route('/tags')
@login_required
@roles_required(['admin', 'editor', 'poster'])
def list_tags():
    if current_user.has_role('admin'):
        tags = Tag.query.order_by(Tag.name.asc()).all()
    else:
        # admin 以外のユーザーは自分のタグのみ表示
        tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name.asc()).all()
    return render_template('tags/list_tags.html', tags=tags, title='タグ管理') # 'admin/tags/list_tags.html' -> 'tags/list_tags.html'

@bp.route('/tags/add', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'editor', 'poster'])
def add_tag():
    form = TagForm()
    if form.validate_on_submit():
        slug = slugify(form.slug.data) if form.slug.data else slugify(form.name.data)
        tag = Tag(name=form.name.data, slug=slug, user_id=current_user.id)
        db.session.add(tag)
        db.session.commit()
        flash('新しいタグが追加されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_tags'))
    return render_template('tags/add_edit_tag.html', form=form, title='タグ追加', is_edit=False) # 'admin/tags/add_edit_tag.html' -> 'tags/add_edit_tag.html'

@bp.route('/tags/edit/<uuid:tag_id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'editor', 'poster'])
def edit_tag(tag_id):
    tag = db.session.get(Tag, tag_id)
    if tag is None:
        flash('タグが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_tags'))

    # タグの所有者または管理者のみが編集可能
    if not (current_user.has_role('admin') or tag.user_id == current_user.id):
        flash('このタグを編集する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_tags'))

    form = TagForm(obj=tag)
    if form.validate_on_submit():
        tag.name = form.name.data
        tag.slug = slugify(form.slug.data) if form.slug.data else slugify(form.name.data)
        db.session.commit()
        flash('タグが更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_tags'))
    elif request.method == 'GET':
        form.name.data = tag.name
        form.slug.data = tag.slug
    return render_template('tags/add_edit_tag.html', form=form, tag=tag, title='タグ編集', is_edit=True) # 'admin/tags/add_edit_tag.html' -> 'tags/add_edit_tag.html'

@bp.route('/tags/delete/<uuid:tag_id>', methods=['POST'])
@login_required
@roles_required(['admin', 'editor', 'poster'])
def delete_tag(tag_id):
    tag_to_delete = db.session.get(Tag, tag_id)
    if not tag_to_delete:
        flash('タグが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_tags'))

    # タグの所有者または管理者のみが削除可能
    if not (current_user.has_role('admin') or tag_to_delete.user_id == current_user.id):
        flash('このタグを削除する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_tags'))

    if tag_to_delete.posts.count() > 0:
        flash(f'このタグにはまだ{tag_to_delete.posts.count()}件の投稿が紐付いています。先にこれらの投稿からタグを解除してください。', 'warning')
        return redirect(url_for('blog_admin_bp.list_tags'))

    try:
        db.session.delete(tag_to_delete)
        db.session.commit()
        flash('タグが削除されました。', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'タグの削除中にエラーが発生しました: {e}', 'danger')

    return redirect(url_for('blog_admin_bp.list_tags'))


# --- 画像管理 ---
@bp.route('/images')
@login_required
@roles_required(['admin', 'editor', 'poster'])
def list_images():
    if current_user.has_role('admin'):
        images = Image.query.order_by(Image.uploaded_at.desc()).all()
    else:
        images = Image.query.filter_by(user_id=current_user.id).order_by(Image.uploaded_at.desc()).all()
    return render_template('images/list_images.html', images=images, title='画像管理') # 'admin/images/list_images.html' -> 'images/list_images.html'

@bp.route('/images/upload', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'editor', 'poster'])
def upload_image():
    form = ImageUploadForm()
    if form.validate_on_submit():
        image_file = form.image_file.data
        if image_file and allowed_file(image_file.filename):
            original_filename = secure_filename(image_file.filename)
            unique_filename = str(uuid.uuid4()) + os.path.splitext(original_filename)[1]
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'images', unique_filename)
            image_file.save(filepath)

            # サムネイル生成
            thumbnail_filename = 'thumb_' + unique_filename
            thumbnail_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'thumbnails', thumbnail_filename)
            try:
                img_pil = PilImage.open(filepath)
                img_pil.thumbnail(THUMBNAIL_SIZE)
                img_pil.save(thumbnail_filepath)
            except Exception as e:
                current_app.logger.error(f"サムネイル生成中にエラーが発生しました: {e}")
                thumbnail_filename = None
                thumbnail_filepath = None
            
            new_image = Image(
                original_filename=original_filename,
                unique_filename=unique_filename,
                thumbnail_filename=thumbnail_filename,
                filepath=f'uploads/images/{unique_filename}',
                thumbnail_filepath=f'uploads/thumbnails/{thumbnail_filename}' if thumbnail_filename else None,
                user_id=current_user.id,
                alt_text=form.alt_text.data
            )
            db.session.add(new_image)
            db.session.commit()
            flash('画像が正常にアップロードされました。', 'success')
            return redirect(url_for('blog_admin_bp.list_images'))
        else:
            flash('無効なファイル形式です。', 'danger')
    return render_template('images/upload_image.html', form=form, title='画像アップロード') # 'admin/images/upload_image.html' -> 'images/upload_image.html'

@bp.route('/images/bulk_upload', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'editor', 'poster'])
def bulk_upload_images():
    form = BulkImageUploadForm()
    if form.validate_on_submit():
        uploaded_count = 0
        failed_count = 0
        for image_file in form.image_files.data:
            if image_file and allowed_file(image_file.filename):
                original_filename = secure_filename(image_file.filename)
                unique_filename = str(uuid.uuid4()) + os.path.splitext(original_filename)[1]
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'images', unique_filename)
                
                try:
                    image_file.save(filepath)

                    # サムネイル生成
                    thumbnail_filename = 'thumb_' + unique_filename
                    thumbnail_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'thumbnails', thumbnail_filename)
                    try:
                        img_pil = PilImage.open(filepath)
                        img_pil.thumbnail(THUMBNAIL_SIZE)
                        img_pil.save(thumbnail_filepath)
                    except Exception as e:
                        current_app.logger.error(f"バルクアップロード中にサムネイル生成エラー: {original_filename} - {e}")
                        thumbnail_filename = None
                        thumbnail_filepath = None

                    new_image = Image(
                        original_filename=original_filename,
                        unique_filename=unique_filename,
                        thumbnail_filename=thumbnail_filename,
                        filepath=f'uploads/images/{unique_filename}',
                        thumbnail_filepath=f'uploads/thumbnails/{thumbnail_filename}' if thumbnail_filename else None,
                        user_id=current_user.id,
                        alt_text="" # バルクアップロードではalt_textは空にするか、後で編集させる
                    )
                    db.session.add(new_image)
                    uploaded_count += 1
                except Exception as e:
                    current_app.logger.error(f"バルクアップロード中にファイル保存エラー: {original_filename} - {e}")
                    failed_count += 1
            else:
                failed_count += 1
        
        if uploaded_count > 0:
            db.session.commit()
            flash(f'{uploaded_count}個の画像を正常にアップロードしました。', 'success')
        if failed_count > 0:
            flash(f'{failed_count}個の画像のアップロードに失敗しました（無効なファイル形式またはエラー）。', 'danger')
        
        return redirect(url_for('blog_admin_bp.list_images'))
    return render_template('images/bulk_upload_images.html', form=form, title='一括画像アップロード') # 'admin/images/bulk_upload_images.html' -> 'images/bulk_upload_images.html'


@bp.route('/images/edit/<uuid:image_id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'editor', 'poster'])
def edit_image(image_id):
    image = db.session.get(Image, image_id)
    if image is None:
        flash('画像が見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_images'))
    
    # 画像の所有者または管理者のみが編集可能
    if not (current_user.has_role('admin') or image.user_id == current_user.id):
        flash('この画像を編集する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_images'))

    form = ImageUploadForm(obj=image) # ImageUploadFormを再利用
    # ImageUploadFormにはimage_fileフィールドがあるが、編集時は使わないのでバリデータを削除
    form.image_file.validators = [Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], '画像ファイル (JPG, JPEG, PNG, GIF, WEBP) のみ許可されます')]


    if form.validate_on_submit():
        # alt_textのみ更新
        image.alt_text = form.alt_text.data
        db.session.commit()
        flash('画像情報が更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_images'))
    elif request.method == 'GET':
        form.alt_text.data = image.alt_text

    return render_template('images/edit_image.html', form=form, image=image, title='画像編集') # 'admin/images/edit_image.html' -> 'images/edit_image.html'


@bp.route('/images/delete/<uuid:image_id>', methods=['POST'])
@login_required
@roles_required(['admin', 'editor', 'poster'])
def delete_image(image_id):
    image_to_delete = db.session.get(Image, image_id)
    if not image_to_delete:
        flash('画像が見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_images'))
    
    # 画像の所有者または管理者のみが削除可能
    if not (current_user.has_role('admin') or image_to_delete.user_id == current_user.id):
        flash('この画像を削除する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_images'))

    # メイン画像として使用されているか確認
    if image_to_delete.post_as_main_image: # backrefから確認
        flash('この画像は投稿のメイン画像として使用されています。先に投稿から画像を解除してください。', 'warning')
        return redirect(url_for('blog_admin_bp.list_images'))

    # 追加画像として使用されているか確認 (多対多リレーションシップの場合)
    if image_to_delete.posts_as_additional_image.count() > 0:
        flash('この画像は複数の投稿の追加画像として使用されています。先に投稿から画像を解除してください。', 'warning')
        return redirect(url_for('blog_admin_bp.list_images'))

    try:
        # 物理ファイルの削除
        if image_to_delete.filepath and os.path.exists(image_to_delete.filepath):
            os.remove(image_to_delete.filepath)
        if image_to_delete.thumbnail_filepath and os.path.exists(image_to_delete.thumbnail_filepath):
            os.remove(image_to_delete.thumbnail_filepath)

        db.session.delete(image_to_delete)
        db.session.commit()
        flash('画像が削除されました。', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'画像の削除中にエラーが発生しました: {e}', 'danger')

    return redirect(url_for('blog_admin_bp.list_images'))


# --- コメント管理 ---
@bp.route('/comments')
@login_required
@roles_required(['admin']) # コメント管理は通常adminのみ
def list_comments():
    comments = Comment.query.order_by(Comment.created_at.desc()).all()
    return render_template('comments/list_comments.html', comments=comments, title='コメント管理') # 'admin/comments/list_comments.html' -> 'comments/list_comments.html'


@bp.route('/comments/edit/<uuid:comment_id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def edit_comment(comment_id):
    comment = db.session.get(Comment, comment_id)
    if not comment:
        flash('コメントが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_comments'))

    form = AdminCommentForm(obj=comment) # ← CommentForm から AdminCommentForm に変更

    if form.validate_on_submit():
        comment.body = form.body.data
        comment.is_approved = form.approved.data
        db.session.commit()
        flash('コメントが更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_comments'))
    elif request.method == 'GET':
        form.body.data = comment.body
        form.approved.data = comment.is_approved
    
    return render_template('comments/edit_comment.html', form=form, comment=comment, title='コメント編集')

@bp.route('/comments/delete/<uuid:comment_id>', methods=['POST']) # 追加: コメント削除ルート
@login_required
@roles_required(['admin'])
def delete_comment(comment_id):
    comment_to_delete = db.session.get(Comment, comment_id)
    if not comment_to_delete:
        flash('コメントが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_comments'))

    try:
        db.session.delete(comment_to_delete)
        db.session.commit()
        flash('コメントが削除されました。', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'コメントの削除中にエラーが発生しました: {e}', 'danger')

    return redirect(url_for('blog_admin_bp.list_comments'))