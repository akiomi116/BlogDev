import os
import uuid
from datetime import datetime
from typing import Optional
from PIL import Image as PILImage

from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import (UserMixin, LoginManager, login_user, login_required, logout_user, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
# DBと秘密鍵の設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///akiomi.db'
app.config['SECRET_KEY'] = '12341234'
# アップロードフォルダ設定
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
# app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # filesize 最大2MB

# DB初期化
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# ✅ 中間テーブル（Post と Tag の多対多用）
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

# モデル定義
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)  # メールアドレス
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(15), nullable=False)  # 投稿者名
    role = db.Column(db.String(10), nullable=False)  # 役割(role)（admin か poster）
    # 投稿への参照を追加
    posts = db.relationship('Post', backref='author', lazy=True)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_filename = db.Column(db.String(200))  # アップロードされた画像のファイル名
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.now())  # ✅ 自動設定
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())
    # メイン画像への参照
    main_image_id = db.Column(db.Integer, db.ForeignKey('image.image_id',ondelete='SET NULL'), nullable=True)
    # 画像（Image）へのリレーションシップ
    images = db.relationship('Image', back_populates='post', foreign_keys='Image.post_id',cascade ='all,delete-orphan')
    #　タグ（Tag）とコメント(Coment）へのリレーションシップ
    tags = db.relationship('Tag', secondary=post_tags, backref='posts')
    comments = db.relationship('Comment', backref='post', cascade="all, delete-orphan")
        
    def __repr__(self):
        return f"<Post(id={self.id}, title={self.title}, author_id={self.author_id})>"

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    # 投稿との関連
    posts = db.relationship('Post', backref='category', lazy=True)
    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name})>"

class Image(db.Model):
    image_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="画像を一意に識別するID")
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False, comment="関連付ける記事ID")
    original_url = db.Column(db.String(255), nullable=False, comment="原画像のパス/URL")
    thumbnail_url = db.Column(db.String(255), nullable=False, comment="サムネイル画像のパス/URL")
    alt_text = db.Column(db.String(255), nullable=True, comment="画像の代替テキスト、SEO/アクセシビリティ向け")
    caption = db.Column(db.Text, nullable=True, comment="画像のキャプション説明")
    display_order = db.Column(db.Integer, default=0, comment="同じ記事内での表示順序")
    is_main_image = db.Column(db.Boolean, default=False, comment="アイキャッチ画像かどうか")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, comment="登録日時")
    # リレーションシップ
    post = db.relationship("Post", foreign_keys=[post_id], back_populates="images")
    # メイン画像として参照される投稿への逆参照
    main_for_posts = db.relationship('Post', foreign_keys='Post.main_image_id',passive_deletes=True)
    
    def __repr__(self):
        return f"<Image(image_id={self.image_id}, post_id={self.post_id}, is_main_image={self.is_main_image})>"

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    # 関連付け（backref で post.tags が使える）
    #posts = db.relationship('Post', secondary=post_tags, backref='tags')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    author_name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.now())

    #post = db.relationship('Post', backref=db.backref('comments', lazy=True, cascade="all, delete-orphan"))

#ヘルパー関数
def setup_upload_folders():
    # メインアップロードディレクトリの確認
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    # サムネイルディレクトリの確認
    thumb_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails')
    if not os.path.exists(thumb_dir):
        os.makedirs(thumb_dir)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_thumbnail(original_path, size=(300, 300)):
    """オリジナル画像からサムネイルを作成する関数"""
    try:
        thumb_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails')
        # サムネイル保存用のディレクトリがない場合は作成
        if not os.path.exists(thumb_dir):
            os.makedirs(thumb_dir)

        # オリジナルファイル名からサムネイル用のファイル名を生成
        filename = os.path.basename(original_path)
        thumbnail_path = os.path.join(thumb_dir, f"thumb_{filename}")

        # PILを使用してサムネイルを作成
        with PILImage.open(original_path) as img:
            img.thumbnail(size)
            img.save(thumbnail_path)

        return thumbnail_path
    except Exception as e:
        print(f"サムネイル作成エラー: {e}")
        return None

"""
def migrate_existing_images():
    既存の投稿からイメージデータを移行する
    posts = Post.query.filter(Post.image_filename.isnot(None)).all()
    for post in posts:
        if post.image_filename:
            original_url = f"/static/uploads/{post.image_filename}"
            # サムネイルが既にあるか確認
            thumbnail_filename = f"thumb_{post.image_filename}"
            thumbnail_path = os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails', thumbnail_filename)
            
            # サムネイルがなければ作成
            if not os.path.exists(thumbnail_path):
                original_path = os.path.join(app.config['UPLOAD_FOLDER'], post.image_filename)
                if os.path.exists(original_path):
                    create_thumbnail(original_path)
            
            thumbnail_url = f"/static/uploads/thumbnails/{thumbnail_filename}"
            
            # すでに存在していないか確認
            existing_image = Image.query.filter_by(post_id=post.id, is_main_image=True).first()
            if not existing_image:
                new_image = Image(
                    post_id=post.id,
                    original_url=original_url,
                    thumbnail_url=thumbnail_url,
                    alt_text=post.title,
                    is_main_image=True
                )
                db.session.add(new_image)
                db.session.flush()
                post.main_image_id = new_image.image_id
    
    db.session.commit()
    print(f"{len(posts)} 件の投稿から画像データを移行しました")
"""

# ログインマネージャーの設定
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ホームページへのアクセスをログインページへリダイレクト
@app.route('/')
def redirect_to_login():
    return redirect(url_for('login'))


# ログイン
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('メールアドレスまたはパスワードが違います')  # エラーメッセージをフラッシュ
            return redirect(url_for('login'))
    return render_template('login.html')

#ユーザー登録
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        role = request.form['role']

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(email=email, username=username,
                        password=hashed_password, name=name, role=role)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))
    return render_template('register.html')


# 記事一覧　ダッシュボード（認証後のページ）
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        posts = Post.query.order_by(Post.created_at.desc()).all()
    else:
        posts = Post.query.filter_by(author_id=current_user.id).order_by(Post.created_at.desc()).all()

    # カテゴリID → 投稿リストの辞書に変換
    from collections import defaultdict
    grouped_posts = defaultdict(list)
    for post in posts:
        grouped_posts[post.category.name if post.category else '未分類'].append(post)

    # ⭐ main_image_id -> Imageオブジェクトの辞書を作成
    image_map = {img.image_id: img for img in Image.query.all()}

    return render_template('dashboard.html', grouped_posts=grouped_posts, image_map=image_map)


#新規投稿
@app.route('/posts/new', methods=['GET', 'POST'])
@login_required
def create_post():
    categories = Category.query.order_by(Category.name).all()
    tags = Tag.query.order_by(Tag.name).all()  # ✅ タグ一覧を取得

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category_id = request.form.get('category')
        published = bool(request.form.get('published'))

        tag_ids = request.form.getlist('tags')  # ✅ タグID一覧を取得
        selected_tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()

        new_post = Post(
            title=title,
            content=content,
            author_id=current_user.id,
            category_id=category_id,
            published=published,
            tags=selected_tags  # ✅ タグを関連付け
        )

        db.session.add(new_post)
        db.session.flush()  # IDを生成する

        # 画像アップロード処理（省略しなければそのまま残す）

        db.session.commit()
        flash('投稿を作成しました')
        return redirect(url_for('dashboard'))

    # GET リクエスト時：カテゴリとタグを渡す
    return render_template('create_post.html', categories=categories, tags=tags)

#投稿編集
@app.route('/posts/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    categories = Category.query.order_by(
        Category.name).all()  # カテゴリデータを取得
    tags = Tag.query.order_by(Tag.name).all()
   
    # 投稿者でない場合は編集を禁止（管理者はOK）
    if post.author_id != current_user.id and current_user.role != 'admin':
        flash('この投稿を編集する権限がありません')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        post.title = request.form['title']
        post.body = request.form['content']
        post.category_id = request.form.get('category')
        post.published = bool(request.form.get('published'))

        # ✅ タグの処理（複数選択版）
        tag_ids = request.form.getlist('tags')  # ['1', '2']
        selected_tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
        post.tags = selected_tags
        
        # 画像処理
        image_file = request.files.get('image')
        if image_file and allowed_file(image_file.filename):
            # 安全なファイル名で保存
            safe_name = secure_filename(image_file.filename)
            unique_name = f"{uuid.uuid4().hex}_{safe_name}"
            original_path = os.path.join(
                app.config['UPLOAD_FOLDER'], unique_name)
            image_file.save(original_path)

            # 後方互換性のため、従来の image_filename も設定
            post.image_filename = unique_name

            # サムネイルを作成
            thumbnail_path = create_thumbnail(original_path)
            if thumbnail_path:
                # パスからURLに変換
                original_url = f"/static/uploads/{unique_name}"
                thumbnail_url = f"/static/uploads/thumbnails/thumb_{unique_name}"

                # 新しい画像を追加する場合
                # メイン画像があるか確認
                main_image = Image.query.filter_by(
                    post_id=post.id, is_main_image=True).first()

                if main_image:
                    # 既存のメイン画像を更新
                    main_image.original_url = original_url
                    main_image.thumbnail_url = thumbnail_url
                    main_image.alt_text = post.title
                else:
                    # 新しいメイン画像を作成
                    new_image = Image(
                        post_id=post.id,
                        original_url=original_url,
                        thumbnail_url=thumbnail_url,
                        alt_text=post.title,
                        is_main_image=True
                    )
                    db.session.add(new_image)
                    db.session.flush()
                    post.main_image_id = new_image.image_id

        db.session.commit()

        flash('投稿を更新しました')
        return redirect(url_for('dashboard'))

    return render_template('edit_post.html', post=post, categories=categories, tags=tags)  
    # 取得したカテゴリ、タグを渡す
   
#投稿削除
@app.route('/posts/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    if post.author_id != current_user.id and current_user.role != 'admin':
        flash('この投稿を削除する権限がありません')
        return redirect(url_for('dashboard'))

    db.session.delete(post)
    db.session.commit()
    flash('投稿を削除しました')
    return redirect(url_for('dashboard'))

@app.route('/posts/<int:post_id>')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post_detail.html', post=post)

# カテゴリ登録
@app.route('/categories/new', methods=['GET', 'POST'])
@login_required
def create_category():
    if current_user.role != 'admin':
        abort(403)  # 管理者以外はアクセス不可

    if request.method == 'POST':
        name = request.form['name'].strip()
        if not name:
            flash("カテゴリ名を入力してください", "danger")
        elif Category.query.filter_by(name=name).first():
            flash("同名のカテゴリがすでに存在します", "warning")
        else:
            db.session.add(Category(name=name))
            db.session.commit()
            flash("カテゴリを登録しました", "success")
            return redirect(url_for('categories.list_categories'))

    return render_template('create_category.html')

#　カテゴリ一覧
@app.route('/categories')
@login_required
def list_categories():
    if current_user.role != 'admin':
        abort(403)

    categories = Category.query.order_by(Category.name).all()

    # カテゴリIDごとの最新投稿を辞書に格納
    latest_posts = {
        category.id: Post.query.filter_by(category_id=category.id)
                               .order_by(Post.created_at.desc())
                               .first()
        for category in categories
    }

    # ✅ main_image用マッピング
    image_map = {img.image_id: img for img in Image.query.all()}

    return render_template(
        'list_categories.html',
        categories=categories,
        latest_posts=latest_posts,
        image_map=image_map
    )

# カテゴリ編集
@app.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    if current_user.role != 'admin':
        abort(403)

    category = Category.query.get_or_404(category_id)
    
    
    if request.method == 'POST':
        new_name = request.form['name'].strip()
        if not new_name:
            flash('カテゴリ名を入力してください', 'danger')
        else:
            category.name = new_name
            db.session.commit()
            flash('カテゴリ名を更新しました', 'success')
            return redirect(url_for('list_categories'))

    return render_template('edit_category.html', category=category)

# カテゴリ一覧
@app.route('/categories/<int:category_id>/posts')
@login_required
def posts_by_category(category_id):
    category = Category.query.get_or_404(category_id)
    posts = Post.query.filter_by(category_id=category.id).order_by(Post.created_at.desc()).all()
    # main_image_id -> Imageオブジェクトの辞書を作成
    image_map = {img.image_id: img for img in Image.query.all()}

    return render_template('posts_by_category.html', category=category, posts=posts, image_map=image_map)

#　カテゴリ削除
@app.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    if current_user.role != 'admin':
        abort(403)

    category = Category.query.get_or_404(category_id)
    if category.posts:  # Post モデルで backref='category' がある前提
        flash('このカテゴリには投稿があるため削除できません', 'warning')
        return redirect(url_for('list_categories'))
    
    db.session.delete(category)
    db.session.commit()
    flash('カテゴリを削除しました', 'success')
    return redirect(url_for('list_categories'))

# タグ管理
@app.route('/tags')
@login_required
def list_tags():
    if current_user.role != 'admin':
        abort(403)
    tags = Tag.query.order_by(Tag.name).all()
    
    # ✅ 各タグに対して代表投稿を取得
    latest_posts = {
        tag.id: tag.posts[-1] if tag.posts else None
        for tag in tags
    }

    # ✅ Image 一括取得
    image_map = {img.image_id: img for img in Image.query.all()}

    return render_template(
        'list_tags.html',
        tags=tags,
        latest_posts=latest_posts,
        image_map=image_map
    )
    
    
@app.route('/tags/new', methods=['GET', 'POST'])
@login_required
def create_tag():
    if current_user.role != 'admin':
        abort(403)
    if request.method == 'POST':
        name = request.form['name'].strip()
        if not name:
            flash("タグ名を入力してください", "danger")
        elif Tag.query.filter_by(name=name).first():
            flash("同名のタグがすでに存在します", "warning")
        else:
            db.session.add(Tag(name=name))
            db.session.commit()
            flash("タグを登録しました", "success")
            return redirect(url_for('list_tags'))
    return render_template('create_tag.html')

@app.route('/tags/<int:tag_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_tag(tag_id):
    if current_user.role != 'admin':
        abort(403)
    tag = Tag.query.get_or_404(tag_id)
    if request.method == 'POST':
        name = request.form['name'].strip()
        if not name:
            flash('タグ名を入力してください', 'danger')
        else:
            tag.name = name
            db.session.commit()
            flash('タグ名を更新しました', 'success')
            return redirect(url_for('list_tags'))
    return render_template('edit_tag.html', tag=tag)

@app.route('/tags/<int:tag_id>/delete', methods=['POST'])
@login_required
def delete_tag(tag_id):
    if current_user.role != 'admin':
        abort(403)
    tag = Tag.query.get_or_404(tag_id)
    if tag.posts:
        flash("このタグは投稿に使われているため削除できません", "warning")
    else:
        db.session.delete(tag)
        db.session.commit()
        flash("タグを削除しました", "success")
    return redirect(url_for('list_tags'))

@app.route('/tags/<int:tag_id>/posts')
@login_required
def posts_by_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    posts = tag.posts
    # main_image_id -> Imageオブジェクトの辞書を作成
    image_map = {img.image_id: img for img in Image.query.all()}

    # デバッグ用：ログを出力
    print(f"Tag: {tag.name}, Posts count: {len(posts)}")
    for post in posts:
        print(f"Post ID: {post.id}, image_filename: {post.image_filename}, main_image_id: {post.main_image_id}")
        if post.main_image_id:
            main_image = image_map.get(post.main_image_id)
            if main_image:
                print(f"  Main image found: {main_image.thumbnail_url}")
            else:
                print(f"  Main image not found for ID: {post.main_image_id}")

    return render_template('posts_by_tag.html', tag=tag, posts=posts, image_map=image_map)



@app.route('/bulk_upload', methods=['GET', 'POST'])
@login_required
def bulk_upload():
    if request.method == 'POST':
        uploaded_files = request.files.getlist('images')
        if not uploaded_files:
            flash('画像が選択されていません', 'warning')
            return redirect(request.url)

        for image in uploaded_files:
            if image and allowed_file(image.filename):
                safe_name = secure_filename(image.filename)
                unique_name = f"{uuid.uuid4().hex}_{safe_name}"
                original_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                image.save(original_path)

                # サムネイル生成
                thumbnail_path = create_thumbnail(original_path)
                thumbnail_url = f"/static/uploads/thumbnails/thumb_{unique_name}" if thumbnail_path else ""

                # DB 登録
                new_post = Post(
                    title="仮タイトル",
                    content="仮の内容です。後で編集してください。",
                    author_id=current_user.id,
                    published=False,
                    image_filename=unique_name,
                    created_at=datetime.utcnow()
                )
                db.session.add(new_post)
                db.session.flush()  # post.id を取得するため flush

                new_image = Image(
                    post_id=new_post.id,
                    original_url=f"/static/uploads/{unique_name}",
                    thumbnail_url=thumbnail_url,
                    alt_text="アップロード画像",
                    is_main_image=True
                )
                db.session.add(new_image)
                db.session.flush()

                # メイン画像参照を設定
                new_post.main_image_id = new_image.image_id

        db.session.commit()
        flash(f'{len(uploaded_files)} 件の画像をアップロードしました', 'success')
        return redirect(url_for('dashboard'))

    return render_template('bulk_upload.html')

# コメント
@app.route('/posts/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    author_name = request.form['author_name']
    content = request.form['content']
    comment = Comment(post_id=post.id, author_name=author_name, content=content)
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('post_detail', post_id=post.id))

@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403

# ログアウト
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.template_filter('nl2br')
def nl2br(value):
    from markupsafe import Markup, escape
    return Markup('<br>\n'.join(escape(value).split('\n')))


# データベースの作成
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        #migrate_existing_images()  # データ移行を実行
    app.run(debug=True)

