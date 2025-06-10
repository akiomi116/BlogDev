# F:\dev\BrogDev\app\models.py

import uuid
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import UUID 
from sqlalchemy.schema import PrimaryKeyConstraint, UniqueConstraint
import pytz
from app.extensions import db

from sqlalchemy_utils import UUIDType
from sqlalchemy.orm import relationship 
from werkzeug.security import generate_password_hash, check_password_hash
from flask import url_for, current_app


# 多対多のリレーションシップ用ヘルパーテーブル
# post_tags テーブル名は大文字小文字を区別せず、単数形にすることが一般的だが、
# ここでは既存の定義に合わせる (post_tags)
post_tags = db.Table(
    'post_tags',
    db.Column('post_id', UUIDType(binary=False), db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', UUIDType(binary=False), db.ForeignKey('tag.id'), primary_key=True)
)

# Post と Additional_Images の多対多リレーションシップのための結合テーブル
# この部分が、これまでのエラー解決に不可欠でした。
post_additional_images = db.Table(
    'post_additional_images', # 結合テーブルの名前
    db.Column('post_id', UUIDType(binary=False), db.ForeignKey('post.id'), primary_key=True),
    db.Column('image_id', UUIDType(binary=False), db.ForeignKey('image.id'), primary_key=True)
)


class Role(db.Model):
    """
    アプリケーションにおけるユーザーの役割を表し、権限やアクセスレベルを定義します。
    """
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True) 
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(256), nullable=True)

    def __repr__(self):
        return f'<Role {self.name}>'

class User(UserMixin, db.Model):
    """
    アプリケーションのユーザーを表し、認証と、ユーザーが作成したコンテンツ
    （投稿、カテゴリ、タグ、画像、コメント）との関係を処理します。
    """
    __tablename__ = 'user'
    id = db.Column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc), onupdate=lambda: datetime.now(pytz.utc), nullable=False)

    role = relationship('Role', backref=db.backref('users', lazy='dynamic'))

    posts = relationship('Post', backref='posted_by', lazy='dynamic', cascade='all, delete-orphan')
    categories = relationship('Category', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    tags = relationship('Tag', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    uploaded_images = relationship('Image', back_populates='uploader', lazy='dynamic', cascade='all, delete-orphan')
    comments = relationship('Comment', backref='comment_author', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def is_admin(self):
        """ユーザーが'Admin'ロールを持っているかチェックするプロパティ"""
        return self.has_role('admin')

    @property
    def is_editor(self):
        """ユーザーが'Editor'ロールを持っているかチェックするプロパティ"""
        return self.has_role('poster')

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        """与えられたパスワードをハッシュ化して保存します。"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """与えられたパスワードが保存されたハッシュと一致するかを確認します。"""
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, role_name):
        """指定されたロールを持っているか汎用的にチェックするメソッド"""
        return self.role is not None and self.role.name == role_name
    
class Category(db.Model):
    """
    投稿を整理するためのカテゴリを表し、特定のユーザーに関連付けられます。
    ユーザーごとにカテゴリ名とスラッグの一意性を保証します。
    """
    __tablename__ = 'category'
    id = db.Column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(128), nullable=False)
    slug = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc), onupdate=lambda: datetime.now(pytz.utc), nullable=False)
    
    user_id = db.Column(UUIDType(binary=False), db.ForeignKey('user.id'), nullable=False)

    __table_args__ = (UniqueConstraint('name', 'user_id', name='_category_name_user_id_uc'),
                      UniqueConstraint('slug', 'user_id', name='_category_slug_user_id_uc'))
    posts = relationship('Post', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'

class Tag(db.Model):
    """
    投稿を分類するためのタグを表し、特定のユーザーに関連付けられます。
    ユーザーごとにタグ名とスラッグの一意性を保証します。
    """
    __tablename__ = 'tag'
    
    id = db.Column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(64), nullable=False)
    slug = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc), onupdate=lambda: datetime.now(pytz.utc), nullable=False)

    user_id = db.Column(UUIDType(binary=False), db.ForeignKey('user.id'), nullable=False)

    __table_args__ = (UniqueConstraint('name', 'user_id', name='_tag_name_user_id_uc'),
                      UniqueConstraint('slug', 'user_id', name='_tag_slug_user_id_uc'))

    def __repr__(self):
        return f'<Tag {self.name}>'

class Image(db.Model):
    """
    ユーザーがアップロードした画像を表し、メイン画像または投稿内の埋め込み画像として使用できます。
    """
    __tablename__ = 'image' 
    id = db.Column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4) 
    original_filename = db.Column(db.String(255), nullable=False)
    # unique_filename が実質的なファイル名として機能
    unique_filename = db.Column(db.String(255), unique=True, nullable=False)
    thumbnail_filename = db.Column(db.String(255), nullable=True) 
    filepath = db.Column(db.String(500), nullable=False) # サーバ上の絶対パスまたは相対パス（推奨）
    thumbnail_filepath = db.Column(db.String(500), nullable=True) # サーバ上の絶対パスまたは相対パス（推奨）
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc))
    user_id = db.Column(UUIDType(binary=False), db.ForeignKey('user.id'), nullable=False) 
    # is_main_image はPostのmain_image_idで管理されるため、このImageモデルでは不要かもしれません
    # ただし、特定のImageが現在どこかの投稿のメイン画像であるかどうかを素早くチェックしたい場合は維持しても良い
    is_main_image = db.Column(db.Boolean, default=False) 
    alt_text = db.Column(db.String(255), nullable=True) 

    # 埋め込み画像としてPostに紐づくための外部キー
    post_id = db.Column(UUIDType(binary=False), db.ForeignKey('post.id'), nullable=True) 

    # リレーションシップ
    uploader = relationship('User', back_populates='uploaded_images') 

    # Imageが紐づくPostへのリレーションシップ（埋め込み画像の場合）
    # foreign_keys: このリレーションシップがImage.post_idを参照することを明示
    post = relationship('Post', back_populates='images', foreign_keys=[post_id]) 

    @property
    def url(self):
        """画像の公開URLを生成します。"""
        # unique_filename を使ってURLを生成
        if current_app:
            return url_for('static', filename=f'uploads/images/{self.unique_filename}')
        return f'/static/uploads/images/{self.unique_filename}'


    @property
    def thumbnail_url(self):
        """サムネイルの公開URLを生成します。"""
        if self.thumbnail_filename:
            if current_app:
                return url_for('static', filename=f'uploads/thumbnails/{self.thumbnail_filename}')
            return f'/static/uploads/thumbnails/{self.thumbnail_filename}'
        # サムネイルがない場合はフルサイズの画像のURLを返すか、Noneを返すかは要件による
        # 今回はNoneを返す（テンプレート側でNoneチェックが必要）
        return None 

    def __repr__(self):
        return f"<Image {self.unique_filename}>"


class Post(db.Model):
    """
    ブログ投稿を表し、そのコンテンツ、公開ステータス、
    および作成者、カテゴリ、タグ、画像との関係を含みます。
    """
    __tablename__ = 'post'
    id = db.Column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(256), nullable=False)
    body = db.Column(db.Text, nullable=False) 
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc), onupdate=lambda: datetime.now(pytz.utc), nullable=False)
    is_published = db.Column(db.Boolean, default=False, nullable=False)

    user_id = db.Column(UUIDType(binary=False), db.ForeignKey('user.id'), nullable=False) # 投稿者
    category_id = db.Column(UUIDType(binary=False), db.ForeignKey('category.id'), nullable=True) # 所属カテゴリ (オプション)
    
    # メイン画像ID - unique=True を維持（一つの画像は一つの投稿のメイン画像にしかなれない）
    main_image_id = db.Column(UUIDType(binary=False), db.ForeignKey('image.id'), unique=True, nullable=True) 

    # PostとImageの一対一リレーションシップ (main_image)
    main_image = relationship(
        'Image', 
        backref=db.backref('post_as_main_image', uselist=False), # uselist=False で一対一を明示
        foreign_keys=[main_image_id], # main_image_id を参照
        post_update=True # 循環参照の警告回避のため
    )
    # backref='post_as_main_image' により、Imageオブジェクト (img) から img.post_as_main_image でPostオブジェクトにアクセス可能

    # PostとImageの一対多リレーションシップ（埋め込み画像）
    # Imageモデルのpost_idを参照し、back_populates='post'と整合させる
    # 'images' はこの投稿に埋め込まれた画像全てを指す
    images = relationship(
        'Image',
        primaryjoin="Post.id == Image.post_id", # このPostのIDがImageのpost_idと一致
        back_populates='post', # Imageモデルの'post'リレーションシップと結合
        foreign_keys=[Image.post_id], # Image.post_idを外部キーとして指定
        cascade='all, delete-orphan' # Postが削除されたら関連する埋め込み画像も削除
    )

    tags = relationship('Tag', secondary=post_tags, backref=db.backref('posts', lazy='dynamic'))

    # ★★★ 追加した additional_images リレーションシップ ★★★
    additional_images = relationship(
        'Image',
        secondary=post_additional_images, # 上部で定義した結合テーブルの名前を指定
        backref=db.backref('posts_as_additional_image', lazy='dynamic')
    )

    comments = relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Post {self.title}>'
        
class Comment(db.Model):
    """
    ユーザーがブログ投稿に対して行ったコメントを表します。
    """
    __tablename__ = 'comment'
    id = db.Column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False) # pytz.utc を使用するように変更
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc), onupdate=lambda: datetime.now(pytz.utc), nullable=False)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)

    user_id = db.Column(UUIDType(binary=False), db.ForeignKey('user.id'), nullable=False) 
    post_id = db.Column(UUIDType(binary=False), db.ForeignKey('post.id'), nullable=False) 

    def __repr__(self):
        return f'<Comment {self.id} on Post {self.post_id}>'