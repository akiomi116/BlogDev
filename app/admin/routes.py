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
from app.admin.forms import (
    UserForm, RoleForm, PostForm, CategoryForm, TagForm, 
    ImageUploadForm, BulkImageUploadForm, CommentForm
)

from .forms import DeleteRoleForm 
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
    total_users = User.query.count()
    total_posts = Post.query.count()
    total_categories = Category.query.count()
    total_tags = Tag.query.count()
    total_images = Image.query.count()
    
    # 承認待ちコメントの数を取得
    pending_comments_count = Comment.query.filter_by(is_approved=False).count()

    # 最近の活動（例: 最新の投稿、コメントなど）
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    recent_comments = Comment.query.order_by(Comment.created_at.desc()).limit(5).all()
    
    # テンプレートパスを修正: 'admin/index.html' -> 'index.html'
    return render_template('index.html',
                            total_users=total_users,
                            total_posts=total_posts,
                            total_categories=total_categories,
                            total_tags=total_tags,
                            total_images=total_images,
                            pending_comments_count=pending_comments_count,
                            recent_posts=recent_posts,
                            recent_comments=recent_comments)

# --- ユーザー管理 ---
@bp.route('/users')
@login_required
@roles_required(['admin']) # Adminロールのみ許可
def manage_users():
    users = User.query.all()
    # テンプレートパスを修正: 'admin/users/manage_users.html' -> 'users/manage_users.html'
    return render_template('users/manage_users.html', users=users)

@bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@roles_required(['admin']) # Adminロールのみ許可
def add_user():
    form = UserForm()
    form.role_id.choices = [(str(role.id), role.name) for role in Role.query.order_by(Role.name).all()]

    if form.validate_on_submit():
        # form.role.data は選択されたRoleのIDになる
        role = Role.query.get(form.role_id.data) 
        if not role:
            flash('選択された役割が見つかりません。', 'danger')
            return redirect(url_for('blog_admin_bp.add_user'))

        new_user = User(
            username=form.username.data,
            email=form.email.data,
            is_active=form.is_active.data,
            # hashed_password はフォームで直接設定されない場合、Userモデルのsetterで処理
            role=role # ★★★ 修正: 選択されたRoleオブジェクトを割り当てる ★★★
        )
        new_user.set_password(form.password.data) # パスワードを設定
        db.session.add(new_user)
        db.session.commit()
        flash('新しいユーザーが作成されました。', 'success')
        return redirect(url_for('blog_admin_bp.manage_users'))
    
    return render_template('users/add_user.html', form=form, title='新規ユーザー追加')


@bp.route('/users/<uuid:user_id>/change_role', methods=['GET', 'POST'])
@login_required
@roles_required(['admin']) # Adminロールのみ許可
def change_user_role(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('ユーザーが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.manage_users'))

    form = UserForm(obj=user) # obj=user で既存のユーザーデータをフォームにロード
    form.role_id.choices = [(str(role.id), role.name) for role in Role.query.order_by(Role.name).all()]
    
    if user.role: # userに役割が設定されている場合
        form.role_id.data = str(user.role.id) # SelectField の data は選択肢の value に合わせる

    if form.validate_on_submit():
        # form.role.data は選択されたRoleのIDになる
        role = Role.query.get(form.role_id.data)
        if not role:
            flash('選択された役割が見つかりません。', 'danger')
            return redirect(url_for('blog_admin_bp.change_user_role', user_id=user.id))

        user.role = role # ★★★ 修正: 選択されたRoleオブジェクトを割り当てる ★★★
        db.session.commit()
        flash(f'{user.username} の役割を {role.name} に変更しました。', 'success')
        return redirect(url_for('blog_admin_bp.manage_users'))
    
    elif request.method == 'GET':
        if user.role:
            form.role_id.data = str(user.role.id) # 既存の役割をセット

    return render_template('users/change_user_role.html', form=form, user=user, title='ユーザー役割変更')


@bp.route('/users/edit/<uuid:user_id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin']) # Adminロールのみ許可
def edit_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('ユーザーが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.manage_users'))

    form = UserForm(original_username=user.username, original_email=user.email, obj=user)
    form.role_id.choices = [(str(role.id), role.name) for role in Role.query.order_by(Role.name).all()]

    if user.role: # userに役割が設定されている場合
        form.role_id.data = str(user.role.id) # SelectField の data は選択肢の value に合わせる

    if form.validate_on_submit():
        # form.role.data は選択されたRoleのIDになる
        role = Role.query.get(form.role_id.data)
        if not role:
            flash('選択された役割が見つかりません。', 'danger')
            return redirect(url_for('blog_admin_bp.edit_user', user_id=user.id))

        user.username = form.username.data
        user.email = form.email.data
        user.is_active = form.is_active.data
        user.role = role # ★★★ 修正: 選択されたRoleオブジェクトを割り当てる ★★★

        if form.password.data: # パスワードが入力された場合のみ更新
            user.set_password(form.password.data)
        
        db.session.commit()
        flash('ユーザー情報が更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.manage_users'))
    
    # GET リクエストの場合、フォームに既存のデータを表示
    elif request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.is_active.data = user.is_active
        if user.role:
            form.role_id.data = str(user.role.id) # 既存の役割をセット
        
    return render_template('users/edit_user.html', form=form, user=user, title='ユーザー編集')

@bp.route('/users/delete/<uuid:user_id>', methods=['POST'])
@login_required
@roles_required(['admin']) # Adminロールのみ許可
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    for post in user.posts.all():
        for comment in post.comments.all():
            db.session.delete(comment)
        
        for image in post.images.all():
            db.session.delete(image)
        
        post.additional_images.clear()
        db.session.delete(post)

    for image in user.uploaded_images.all():
        if os.path.exists(image.filepath):
            os.remove(image.filepath)
        if image.thumbnail_filepath and os.path.exists(image.thumbnail_filepath):
            os.remove(image.thumbnail_filepath)
        db.session.delete(image)

    for comment in user.comments.all():
        db.session.delete(comment)
    
    db.session.delete(user)
    db.session.commit()
    flash('ユーザーが削除されました。', 'success')
    return redirect(url_for('blog_admin_bp.manage_users'))

# --- ロール管理 ---
@bp.route('/roles')
@login_required
@roles_required(['admin']) # Adminロールのみ許可
def manage_roles():
    roles = Role.query.all()
    form = DeleteRoleForm()
    # テンプレートパスを修正: 'admin/roles/manage_roles.html' -> 'roles/manage_roles.html'
    return render_template('roles/manage_roles.html', roles=roles, form=form)

@bp.route('/roles/new', methods=['GET', 'POST'])
@login_required
@roles_required(['admin']) # Adminロールのみ許可
def new_role():
    form = RoleForm() 
    if form.validate_on_submit():
        role = Role(name=form.name.data)
        db.session.add(role)
        db.session.commit()
        flash('新しいロールが追加されました。', 'success')
        return redirect(url_for('blog_admin_bp.manage_roles'))
    # テンプレートパスを修正: 'admin/roles/new_role.html' -> 'roles/new_role.html'
    return render_template('roles/new_role.html', form=form)

@bp.route('/roles/edit/<int:role_id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin']) # Adminロールのみ許可
def edit_role(role_id):
    role = Role.query.get_or_404(role_id)
    form = RoleForm(obj=role)
    if form.validate_on_submit():
        role.name = form.name.data
        db.session.commit()
        flash('ロール名が更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.manage_roles'))
    # テンプレートパスを修正: 'admin/roles/edit_role.html' -> 'roles/edit_role.html'
    return render_template('roles/edit_role.html', form=form, role=role)

@bp.route('/roles/delete/<int:role_id>', methods=['POST'])
@login_required
@roles_required(['admin'])
def delete_role(role_id):
    form = DeleteRoleForm()
    if form.validate_on_submit(): # CSRFトークン検証
        role = Role.query.get_or_404(role_id)
        for user in role.users.all():
            user.role = None
            db.session.add(user)
        
        db.session.delete(role) 
        db.session.commit()
        flash('ロールが削除されました。', 'success')
    else:
        flash('エラー: 不正なリクエストです。', 'danger')
    return redirect(url_for('blog_admin_bp.manage_roles'))


# --- 投稿管理 ---
@bp.route('/posts')
@login_required
@roles_required(['admin', 'editor', 'poster']) # 適切なロールを設定
def list_posts():
    posts = Post.query.all()
    # テンプレートパスを修正: 'admin/posts/list_posts.html' -> 'posts/list_posts.html'
    return render_template('posts/list_posts.html', posts=posts)

@bp.route('/posts/new', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'poster']) # AdminまたはPosterロールを許可
def new_post():
    form = PostForm()

    if form.validate_on_submit():
        main_image_obj = None

        if form.main_image_file.data:
            uploaded_file = form.main_image_file.data
            upload_folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)
            
            unique_filename = str(uuid.uuid4()) + os.path.splitext(uploaded_file.filename)[1]
            filepath = os.path.join(upload_folder, unique_filename)
            uploaded_file.save(filepath)

            main_image_obj = Image(
                original_filename=uploaded_file.filename,
                unique_filename=unique_filename,
                filepath=filepath,
                user_id=current_user.id,
                alt_text=form.alt_text.data if hasattr(form, 'alt_text') else None
            )
            db.session.add(main_image_obj)
            db.session.flush()

            try:
                thumbnail_folder = current_app.config['THUMBNAIL_FOLDER']
                os.makedirs(thumbnail_folder, exist_ok=True)
                thumbnail_filename = 'thumb_' + unique_filename
                thumbnail_filepath = os.path.join(thumbnail_folder, thumbnail_filename)

                img = PilImage.open(filepath)
                img.thumbnail(THUMBNAIL_SIZE)
                img.save(thumbnail_filepath)

                main_image_obj.thumbnail_filename = thumbnail_filename
                main_image_obj.thumbnail_filepath = thumbnail_filepath
                db.session.add(main_image_obj)
            except Exception as e:
                current_app.logger.warning(f"Failed to generate thumbnail for {unique_filename}: {e}")

        elif form.main_image.data:
            main_image_id = form.main_image.data
            main_image_obj = Image.query.get(main_image_id)
            if not main_image_obj:
                flash('選択されたメイン画像が見つかりませんでした。', 'danger')
                # テンプレートパスを修正: 'admin/posts/new_post.html' -> 'posts/new_post.html'
                return render_template('posts/new_post.html', form=form, title='新規投稿')

        post = Post(
            title=form.title.data,
            body=form.body.data,
            is_published=form.is_published.data
        )

        post.posted_by = current_user
        post.user_id = current_user.id

        db.session.add(post) 

        if main_image_obj:
            post.main_image = main_image_obj

        if form.category.data:
            category = Category.query.get(form.category.data)
            if category:
                post.category = category

        post.tags.clear()
        if form.tags.data:
            for tag_id in form.tags.data:
                tag = Tag.query.get(tag_id)
                if tag:
                    post.tags.append(tag)
        
        post.additional_images.clear()
        if form.additional_images.data:
            for img_id in form.additional_images.data:
                img = Image.query.get(img_id)
                if img:
                    post.additional_images.append(img)

        try:
            db.session.commit()
            flash('新しい投稿が作成されました！', 'success')
            return redirect(url_for('blog_admin_bp.list_posts'))
        except Exception as e:
            db.session.rollback()
            flash(f'投稿の保存中にエラーが発生しました: {e}', 'danger')
            current_app.logger.error(f"Error saving post: {e}")
            # テンプレートパスを修正: 'admin/posts/new_post.html' -> 'posts/new_post.html'
            return render_template('posts/new_post.html', form=form, title='新規投稿')

    # テンプレートパスを修正: 'admin/posts/new_post.html' -> 'posts/new_post.html'
    return render_template('posts/new_post.html', form=form, title='新規投稿')


@bp.route('/posts/edit/<uuid:post_id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'poster']) # AdminまたはPosterロールを許可
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)

    if not current_user.has_role('admin') and post.user_id != current_user.id:
        flash('この投稿を編集する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_posts'))

    form = PostForm()

    if form.validate_on_submit():
        if form.main_image_file.data:
            uploaded_file = form.main_image_file.data
            upload_folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)
            
            unique_filename = str(uuid.uuid4()) + os.path.splitext(uploaded_file.filename)[1]
            filepath = os.path.join(upload_folder, unique_filename)
            uploaded_file.save(filepath)

            main_image_obj = Image(
                original_filename=uploaded_file.filename,
                unique_filename=unique_filename,
                filepath=filepath,
                user_id=current_user.id,
                alt_text=form.alt_text.data if hasattr(form, 'alt_text') else None
            )
            db.session.add(main_image_obj)
            db.session.flush()

            try:
                thumbnail_folder = current_app.config['THUMBNAIL_FOLDER']
                os.makedirs(thumbnail_folder, exist_ok=True)
                thumbnail_filename = 'thumb_' + unique_filename
                thumbnail_filepath = os.path.join(thumbnail_folder, thumbnail_filename)

                img = PilImage.open(filepath)
                img.thumbnail(THUMBNAIL_SIZE)
                img.save(thumbnail_filepath)

                main_image_obj.thumbnail_filename = thumbnail_filename
                main_image_obj.thumbnail_filepath = thumbnail_filepath
                db.session.add(main_image_obj)
            except Exception as e:
                current_app.logger.warning(f"Failed to generate thumbnail for {unique_filename}: {e}")
            
            post.main_image = main_image_obj

        elif form.main_image.data:
            main_image_id = form.main_image.data
            if main_image_id == '':
                post.main_image = None
            else:
                main_image_obj = Image.query.get(main_image_id)
                if main_image_obj:
                    post.main_image = main_image_obj
                else:
                    flash('選択された既存のメイン画像が見つかりませんでした。', 'danger')
                    # テンプレートパスを修正: 'admin/posts/edit_post.html' -> 'posts/edit_post.html'
                    return render_template('posts/edit_post.html', form=form, post=post, title='投稿編集')

        post.title = form.title.data
        post.body = form.body.data
        post.is_published = form.is_published.data

        if form.category.data:
            category = Category.query.get(form.category.data)
            if category:
                post.category = category
            else:
                post.category = None
        else:
            post.category = None

        post.tags.clear()
        if form.tags.data:
            for tag_id in form.tags.data:
                tag = Tag.query.get(tag_id)
                if tag:
                    post.tags.append(tag)
        
        post.additional_images.clear()
        if form.additional_images.data:
            for img_id in form.additional_images.data:
                img = Image.query.get(img_id)
                if img:
                    post.additional_images.append(img)

        try:
            db.session.commit()
            flash('投稿が更新されました！', 'success')
            return redirect(url_for('blog_admin_bp.list_posts'))
        except Exception as e:
            db.session.rollback()
            flash(f'投稿の保存中にエラーが発生しました: {e}', 'danger')
            current_app.logger.error(f"Error saving post: {e}")
            # テンプレートパスを修正: 'admin/posts/edit_post.html' -> 'posts/edit_post.html'
            return render_template('posts/edit_post.html', form=form, post=post, title='投稿編集')

    elif request.method == 'GET':
        form.title.data = post.title
        form.body.data = post.body
        form.is_published.data = post.is_published
        
        if post.category:
            form.category.data = str(post.category.id)
        else:
            form.category.data = ''

        if post.main_image:
            form.main_image.data = str(post.main_image.id)
        else:
            form.main_image.data = ''

        form.tags.data = [str(tag.id) for tag in post.tags]
        form.additional_images.data = [str(img.id) for img in post.additional_images]

    # テンプレートパスを修正: 'admin/posts/edit_post.html' -> 'posts/edit_post.html'
    return render_template('posts/edit_post.html', form=form, post=post, title='投稿編集')

@bp.route('/delete_post/<uuid:post_id>', methods=['POST'])
@login_required
@roles_required(['admin', 'editor']) # 適切なロールを設定
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if not current_user.has_role('admin') and post.user_id != current_user.id:
        flash('この投稿を削除する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_posts'))

    for comment in post.comments.all():
        db.session.delete(comment)
    
    for image in post.images.all():
        image.post_id = None
        db.session.add(image)

    if post.main_image:
        post.main_image = None
    
    post.additional_images.clear()

    db.session.delete(post)
    db.session.commit()
    flash('投稿が削除されました。', 'success')
    return redirect(url_for('blog_admin_bp.list_posts'))

@bp.route('/toggle_publish/<uuid:post_id>', methods=['POST'])
@login_required
@roles_required(['admin', 'editor', 'poster']) # 適切なロールを設定
def toggle_publish(post_id):
    post = Post.query.get_or_404(post_id)
    if not current_user.has_role('admin') and post.user_id != current_user.id:
        flash('この投稿の公開状態を変更する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_posts'))

    post.is_published = not post.is_published
    db.session.commit()
    flash(f'投稿「{post.title}」の公開状態が{"公開" if post.is_published else "非公開"}に変更されました。', 'success')
    return redirect(url_for('blog_admin_bp.list_posts'))

# --- カテゴリ管理 ---
@bp.route('/categories')
@login_required
@roles_required(['admin', 'editor']) # 適切なロールを設定
def manage_categories():
    categories = Category.query.all()
    form = CategoryForm()
    # テンプレートパスを修正: 'admin/categories/manage_categories.html' -> 'categories/manage_categories.html'
    return render_template('categories/manage_categories.html', categories=categories, form=form)

@bp.route('/categories/new', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'editor', 'poster']) # Admin, Editor, Posterロールを許可
def new_category():
    form = CategoryForm()
    if form.validate_on_submit():
        if form.slug.data:
            slug = slugify(form.slug.data)
        else:
            slug = slugify(form.name.data)

        existing_category = Category.query.filter_by(user_id=current_user.id, slug=slug).first()
        if existing_category:
            flash('指定されたスラッグは既に存在します。別のスラッグを使用してください。', 'danger')
            return render_template('categories/new_category.html', form=form, title='新しいカテゴリを作成')

        category = Category(
            name=form.name.data,
            slug=slug,
            description=form.description.data,
            user_id=current_user.id
        )
        db.session.add(category)
        try:
            db.session.commit()
            flash('新しいカテゴリが追加されました。', 'success')
            return redirect(url_for('blog_admin_bp.manage_categories'))
        except Exception as e:
            db.session.rollback()
            flash(f'カテゴリの保存中にエラーが発生しました: {e}', 'danger')
            current_app.logger.error(f"Error saving category: {e}")
            return render_template('categories/new_category.html', form=form, title='新しいカテゴリを作成')
    return render_template('categories/new_category.html', form=form, title='新しいカテゴリを作成')

@bp.route('/categories/edit/<uuid:category_id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'editor']) # AdminまたはEditorロールを許可
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    if not current_user.has_role('admin') and category.user_id != current_user.id:
        flash('このカテゴリを編集する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.manage_categories'))

    form = CategoryForm(obj=category)
    if form.validate_on_submit():
        if form.slug.data:
            slug = slugify(form.slug.data)
        else:
            slug = slugify(form.name.data)

        existing_category = Category.query.filter(
            Category.user_id == current_user.id,
            Category.slug == slug,
            Category.id != category_id
        ).first()

        if existing_category:
            flash('指定されたスラッグは既に存在します。別のスラッグを使用してください。', 'danger')
            # テンプレートパスを修正: 'admin/categories/edit_category.html' -> 'categories/edit_category.html'
            return render_template('categories/edit_category.html', form=form, category=category)

        category.name = form.name.data
        category.slug = slug
        category.description = form.description.data
        try:
            db.session.commit()
            flash('カテゴリ名が更新されました。', 'success')
            return redirect(url_for('blog_admin_bp.manage_categories'))
        except Exception as e:
            db.session.rollback()
            flash(f'カテゴリの更新中にエラーが発生しました: {e}', 'danger')
            current_app.logger.error(f"Error updating category: {e}")
            # テンプレートパスを修正: 'admin/categories/edit_category.html' -> 'categories/edit_category.html'
            return render_template('categories/edit_category.html', form=form, category=category)
    
    elif request.method == 'GET':
        form.name.data = category.name
        form.slug.data = category.slug
        form.description.data = category.description

    # テンプレートパスを修正: 'admin/categories/edit_category.html' -> 'categories/edit_category.html'
    return render_template('categories/edit_category.html', form=form, category=category)

@bp.route('/categories/delete/<uuid:category_id>', methods=['POST'])
@login_required
@roles_required(['admin', 'editor']) # AdminまたはEditorロールを許可
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    if not current_user.has_role('admin') and category.user_id != current_user.id:
        flash('このカテゴリを削除する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.manage_categories'))

    for post in category.posts.all():
        post.category_id = None
        db.session.add(post)

    db.session.delete(category)
    db.session.commit()
    flash('カテゴリが削除されました。', 'success')
    return redirect(url_for('blog_admin_bp.manage_categories'))

# --- タグ管理 ---
@bp.route('/tags')
@login_required
@roles_required(['admin', 'editor']) # 適切なロールを設定
def manage_tags():
    tags = Tag.query.all()
    form = TagForm()
    # テンプレートパスを修正: 'admin/tags/manage_tags.html' -> 'tags/manage_tags.html'
    return render_template('tags/manage_tags.html', tags=tags, form=form)

@bp.route('/tags/new', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'editor']) # AdminまたはEditorロールを許可
def new_tag():
    form = TagForm()
    if form.validate_on_submit():
        if form.slug.data:
            slug = slugify(form.slug.data)
        else:
            slug = slugify(form.name.data)

        existing_tag = Tag.query.filter_by(user_id=current_user.id, slug=slug).first()
        if existing_tag:
            flash('指定されたスラッグは既に存在します。別のスラッグを使用してください。', 'danger')
            # テンプレートパスを修正: 'admin/tags/new_tag.html' -> 'tags/new_tag.html'
            return render_template('tags/new_tag.html', form=form, title='新しいタグを作成')

        tag = Tag(
            name=form.name.data,
            slug=slug,
            user_id=current_user.id
        )
        db.session.add(tag)
        try:
            db.session.commit()
            flash('新しいタグが追加されました。', 'success')
            return redirect(url_for('blog_admin_bp.manage_tags'))
        except Exception as e:
            db.session.rollback()
            flash(f'タグの保存中にエラーが発生しました: {e}', 'danger')
            current_app.logger.error(f"Error saving tag: {e}")
            # テンプレートパスを修正: 'admin/tags/new_tag.html' -> 'tags/new_tag.html'
            return render_template('tags/new_tag.html', form=form, title='新しいタグを作成')
    # テンプレートパスを修正: 'admin/tags/new_tag.html' -> 'tags/new_tag.html'
    return render_template('tags/new_tag.html', form=form, title='新しいタグを作成')

@bp.route('/tags/edit/<uuid:tag_id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'editor']) # AdminまたはEditorロールを許可
def edit_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    if not current_user.has_role('admin') and tag.user_id != current_user.id:
        flash('このタグを編集する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.manage_tags'))

    form = TagForm(obj=tag)
    if form.validate_on_submit():
        if form.slug.data:
            slug = slugify(form.slug.data)
        else:
            slug = slugify(form.name.data)

        existing_tag = Tag.query.filter(
            Tag.user_id == current_user.id,
            Tag.slug == slug,
            Tag.id != tag_id
        ).first()

        if existing_tag:
            flash('指定されたスラッグは既に存在します。別のスラッグを使用してください。', 'danger')
            # テンプレートパスを修正: 'admin/tags/edit_tag.html' -> 'tags/edit_tag.html'
            return render_template('tags/edit_tag.html', form=form, tag=tag)

        tag.name = form.name.data
        tag.slug = slug
        try:
            db.session.commit()
            flash('タグ名が更新されました。', 'success')
            return redirect(url_for('blog_admin_bp.manage_tags'))
        except Exception as e:
            db.session.rollback()
            flash(f'タグの更新中にエラーが発生しました: {e}', 'danger')
            current_app.logger.error(f"Error updating tag: {e}")
            # テンプレートパスを修正: 'admin/tags/edit_tag.html' -> 'tags/edit_tag.html'
            return render_template('tags/edit_tag.html', form=form, tag=tag)
    elif request.method == 'GET':
        form.name.data = tag.name
        form.slug.data = tag.slug

    # テンプレートパスを修正: 'admin/tags/edit_tag.html' -> 'tags/edit_tag.html'
    return render_template('tags/edit_tag.html', form=form, tag=tag)

@bp.route('/tags/delete/<uuid:tag_id>', methods=['POST'])
@login_required
@roles_required(['admin', 'editor']) # AdminまたはEditorロールを許可
def delete_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    if not current_user.has_role('admin') and tag.user_id != current_user.id:
        flash('このタグを削除する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.manage_tags'))
    
    for post in tag.posts.all():
        post.tags.remove(tag)
    
    db.session.delete(tag)
    db.session.commit()
    flash('タグが削除されました。', 'success')
    return redirect(url_for('blog_admin_bp.manage_tags'))


# --- 画像管理 ---
@bp.route('/images')
@login_required
@roles_required(['admin', 'editor', 'poster']) # 適切なロールを設定
def list_images():
    images = Image.query.order_by(Image.uploaded_at.desc()).all()
    # テンプレートパスを修正: 'admin/images/list_images.html' -> 'images/list_images.html'
    return render_template('images/list_images.html', images=images)

# 新しい画像データをJSONで返すエンドポイントを追加
@bp.route('/uploads/images/json', methods=['GET'])
@login_required
@roles_required(['admin', 'editor', 'poster'])
def get_images_json():
    # 管理者の場合は全ての画像を、それ以外のユーザーは自身の画像を返す
    if current_user.has_role('admin'):
        images = Image.query.all()
    else:
        images = Image.query.filter_by(user_id=current_user.id).all()

    image_data = []
    for img in images:
        image_data.append({
            'id': str(img.id),
            'original_filename': img.original_filename,
            'unique_filename': img.unique_filename,
            'url': url_for('static', filename='uploads/images/' + img.unique_filename),
            'thumbnail_url': url_for('static', filename='uploads/thumbnails/' + img.thumbnail_filename) if img.thumbnail_filename else None,
            'alt_text': img.alt_text
        })
    return jsonify(image_data)

@bp.route('/images/upload', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'editor', 'poster']) # 適切なロールを設定
def upload_image():
    form = ImageUploadForm()
    if form.validate_on_submit():
        file = form.image_file.data
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                unique_filename = str(uuid.uuid4()) + os.path.splitext(filename)[1]

                image_full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                thumbnail_full_path = os.path.join(current_app.config['THUMBNAIL_FOLDER'], 'thumb_' + unique_filename)

                file.save(image_full_path)

                thumb_filename_for_db = None
                thumb_filepath_for_db = None
                try:
                    img = PilImage.open(image_full_path)
                    img.thumbnail(THUMBNAIL_SIZE)
                    img.save(thumbnail_full_path)
                    thumb_filename_for_db = 'thumb_' + unique_filename
                    thumb_filepath_for_db = thumbnail_full_path
                except Exception as thumb_e:
                    current_app.logger.warning(f"Failed to generate thumbnail for {filename}: {thumb_e}")

                new_image = Image(
                    original_filename=filename,
                    unique_filename=unique_filename,
                    filepath=image_full_path,
                    thumbnail_filename=thumb_filename_for_db,
                    thumbnail_filepath=thumb_filepath_for_db,
                    user_id=current_user.id,
                    alt_text=form.alt_text.data
                )
                db.session.add(new_image)
                db.session.commit()
                flash('画像が正常にアップロードされました。', 'success')
                return redirect(url_for('blog_admin_bp.list_images'))
            except Exception as e:
                db.session.rollback()
                flash(f'画像のアップロード中にエラーが発生しました: {e}', 'danger')
                current_app.logger.error(f"Error uploading single image: {e}", exc_info=True)
        else:
            flash('許可されていないファイル形式です。', 'danger')
    # テンプレートパスを修正: 'admin/images/upload_single_image.html' -> 'images/upload_single_image.html'
    return render_template('images/upload_single_image.html', form=form)


@bp.route('/images/bulk_upload_form')
@login_required
@roles_required(['admin', 'editor', 'poster']) # 適切なロールを設定
def show_bulk_upload_form():
    form = BulkImageUploadForm()
    # テンプレートパスを修正: 'admin/images/bulk_upload_form.html' -> 'images/bulk_upload_form.html'
    return render_template('images/bulk_upload_form.html', form=form)

@bp.route('/images/bulk_upload', methods=['POST'])
@login_required
@roles_required(['admin', 'editor', 'poster']) # 適切なロールを設定
def bulk_upload_images():
    form = BulkImageUploadForm()
    if form.validate_on_submit():
        uploaded_files = form.image_files.data
        
        if not uploaded_files:
            flash('ファイルを一つ以上選択してください。', 'warning')
            return redirect(url_for('blog_admin_bp.show_bulk_upload_form'))

        upload_success_count = 0
        upload_fail_count = 0
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                try:
                    filename = secure_filename(file.filename)
                    unique_filename = str(uuid.uuid4()) + os.path.splitext(filename)[1]
                    
                    image_full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                    thumbnail_full_path = os.path.join(current_app.config['THUMBNAIL_FOLDER'], 'thumb_' + unique_filename)

                    file.save(image_full_path)
                    
                    thumb_filename_for_db = None
                    thumb_filepath_for_db = None

                    try:
                        img = PilImage.open(image_full_path)
                        img.thumbnail(THUMBNAIL_SIZE) 
                        img.save(thumbnail_full_path)
                        thumb_filename_for_db = 'thumb_' + unique_filename
                        thumb_filepath_for_db = thumbnail_full_path
                    except Exception as thumb_e:
                        current_app.logger.warning(f"Failed to generate thumbnail for {filename}: {thumb_e}")

                    new_image = Image(
                        original_filename=filename,
                        unique_filename=unique_filename,
                        filepath=image_full_path,
                        thumbnail_filename=thumb_filename_for_db,
                        thumbnail_filepath=thumb_filepath_for_db,
                        user_id=current_user.id,
                        is_main_image=False,
                        alt_text=None
                    )
                    db.session.add(new_image)
                    db.session.commit()
                    upload_success_count += 1
                except Exception as e:
                    db.session.rollback()
                    flash(f'ファイル {file.filename} のアップロード中にエラーが発生しました: {e}', 'danger')
                    current_app.logger.error(f"Error uploading file {file.filename}: {e}", exc_info=True)
                    upload_fail_count += 1
            else:
                flash(f'ファイル {file.filename} は許可されていないファイル形式です。', 'warning')
                upload_fail_count += 1
        
        if upload_success_count > 0:
            flash(f'{upload_success_count} 個の画像が正常にアップロードされました。', 'success')
        if upload_fail_count > 0:
            flash(f'{upload_fail_count} 個の画像のアップロードに失敗しました。詳細についてはログを確認してください。', 'warning')
        
        return redirect(url_for('blog_admin_bp.list_images'))
    
    # テンプレートパスを修正: 'admin/images/bulk_upload_form.html' -> 'images/bulk_upload_form.html'
    return render_template('images/bulk_upload_form.html', form=form)

@bp.route('/images/delete/<uuid:image_id>', methods=['POST'], endpoint='delete_image')
@login_required
def delete_image(image_id):
    # 削除処理省略
    flash('画像を削除しました')
    return redirect(url_for('blog_admin_bp.list_images'))


# --- コメント管理 ---
@bp.route('/comments')
@login_required
@roles_required(['admin', 'editor', 'poster']) # 適切なロールを設定
def list_comments():
    comments = Comment.query.order_by(Comment.timestamp.desc()).all()
    # テンプレートパスを修正: 'admin/comments/list_comments.html' -> 'comments/list_comments.html'
    return render_template('comments/list_comments.html', comments=comments)

@bp.route('/comments/approve/<uuid:comment_id>', methods=['POST'])
@login_required
@roles_required(['admin', 'editor']) # 管理者と編集者のみ承認可能
def approve_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    comment.is_approved = True
    db.session.commit()
    flash('コメントが承認されました。', 'success')
    return redirect(url_for('blog_admin_bp.list_comments'))


@bp.route('/comments/edit/<uuid:comment_id>', methods=['GET', 'POST']) # ★追加: コメント編集ルート ★
@login_required
@roles_required(['admin'])
def edit_comment(comment_id):
    comment = db.session.get(Comment, comment_id)
    if not comment:
        flash('コメントが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_comments'))

    form = CommentForm(obj=comment) # 既存のコメントデータをフォームにロード

    if form.validate_on_submit():
        comment.body = form.body.data # ★修正: body にアクセス ★
        comment.is_approved = form.approved.data
        db.session.commit()
        flash('コメントが更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_comments'))
    elif request.method == 'GET':
        form.body.data = comment.body # ★修正: body にアクセス ★
        form.approved.data = comment.is_approved # モデルの is_approved をフォームの approved にセット
    
    return render_template('comments/edit_comment.html', form=form, comment=comment, title='コメント編集')

@bp.route('/comments/delete/<uuid:comment_id>', methods=['POST']) # ★追加: コメント削除ルート ★
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
        flash(f'コメント削除中にエラーが発生しました: {e}', 'danger')
    
    return redirect(url_for('blog_admin_bp.list_comments'))

def register_admin_routes(admin_bp):
    # ここに全てのルート定義を移動します
    pass # 仮のpass文