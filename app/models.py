# F:\dev\BrogDev\app\models.py (修正版)

import os
import uuid
from datetime import datetime
from flask_security import UserMixin, RoleMixin
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.schema import PrimaryKeyConstraint, UniqueConstraint
import pytz
from app.extensions import db

from sqlalchemy_utils import UUIDType
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask import url_for, current_app


# 多対多のリレーションシップ用ヘルパーテーブル
post_tags = db.Table(
    'post_tags',
    db.Column('post_id', UUIDType(binary=False), db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', UUIDType(binary=False), db.ForeignKey('tag.id'), primary_key=True)
)

# Post と Additional_Images の多対多リレーションシップのための結合テーブル
post_additional_images = db.Table(
    'post_additional_images', # 結合テーブルの名前
    db.Column('post_id', UUIDType(binary=False), db.ForeignKey('post.id'), primary_key=True),
    db.Column('image_id', UUIDType(binary=False), db.ForeignKey('image.id'), primary_key=True)
)


class Role(db.Model, RoleMixin):
    """
    アプリケーションにおけるユーザーの役割を表し、権限やアクセスレベルを定義します。
    """
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(256), nullable=True)
    permissions = db.Column(db.JSON)

    def __repr__(self):
        return f'<Role {self.name}>'

roles_users = db.Table(
    'roles_users',
    db.Column('user_id', UUIDType(binary=False), db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)
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
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)
    active = db.Column(db.Boolean(), default=True) # デフォルトでTrueに設定することが重要
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc), onupdate=lambda: datetime.now(pytz.utc), nullable=False)

    # Flask-Security-Too trackable fields
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(100))
    current_login_ip = db.Column(db.String(100))
    login_count = db.Column(db.Integer)

    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))
    # role = relationship('Role', backref=db.backref('users', lazy='dynamic'))
    
    posts = relationship('Post', back_populates='posted_by', lazy='dynamic', cascade='all, delete-orphan')
    categories = relationship('Category', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    tags = relationship('Tag', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    uploaded_images = relationship('Image', back_populates='uploader', lazy='dynamic', cascade='all, delete-orphan')
    comments = relationship('Comment', back_populates='comment_author', lazy='dynamic', cascade='all, delete-orphan')

    def __init__(self, *args, **kwargs):
        """
        新しいUserインスタンスが作成されるときに、fs_uniquifierを自動的に生成します。
        """
        super().__init__(*args, **kwargs)
        if self.fs_uniquifier is None:
            self.fs_uniquifier = str(uuid.uuid4())

    @property
    def is_admin(self):
        """ユーザーが'admin'ロールを持っているかチェックするプロパティ"""
        return self.has_role('admin')

    @property
    def is_editor(self):
        """ユーザーが'Editor'ロールを持っているかチェックするプロパティ"""
        return self.has_role('poster') # ここは'poster'で正しいですか？'editor'の方が自然かもしれません

    def __repr__(self):
        return f'<User {self.username}>'

    @property
    def password(self):
        return self.password_hash

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def set_password(self, password):
        """与えられたパスワードをハッシュ化して保存します。"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """与えられたパスワードが保存されたハッシュと一致するかを確認します。"""
        return check_password_hash(self.password_hash, password)

    def verify_and_update_password(self, password):
        return self.check_password(password)
    
    def has_role(self, role_name):
        """指定されたロールを持っているか汎用的にチェックするメソッド"""
        return any(role.name == role_name for role in self.roles)
    
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
    
    posts = relationship('Post', back_populates='category', lazy='dynamic')

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
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc), onupdate=lambda: datetime.now(pytz.utc), nullable=False)

    user_id = db.Column(UUIDType(binary=False), db.ForeignKey('user.id'), nullable=False)

    __table_args__ = (UniqueConstraint('name', 'user_id', name='_tag_name_user_id_uc'),
                    UniqueConstraint('slug', 'user_id', name='_tag_slug_user_id_uc'))

    def __repr__(self):
        return f'<Tag {self.name}>'

class Image(db.Model):
    __tablename__ = 'image' 
    id = db.Column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4) 
    original_filename = db.Column(db.String(255), nullable=False)
    unique_filename = db.Column(db.String(255), unique=True, nullable=False)
    thumbnail_filename = db.Column(db.String(255), nullable=True) 
    filepath = db.Column(db.String(500), nullable=False)
    thumbnail_filepath = db.Column(db.String(500), nullable=True)
    
    mimetype = db.Column(db.String(100), nullable=True)

    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc))
    user_id = db.Column(UUIDType(binary=False), db.ForeignKey('user.id'), nullable=False) 
    is_main_image = db.Column(db.Boolean, default=False) 
    alt_text = db.Column(db.String(255), nullable=True) 

    post_id = db.Column(UUIDType(binary=False), db.ForeignKey('post.id'), nullable=True) 

    uploader = relationship('User', back_populates='uploaded_images') 
    post = relationship('Post', back_populates='images', foreign_keys=[post_id]) 

    main_image_for_post = relationship('Post', back_populates='main_image', uselist=False, foreign_keys='Post.main_image_id', overlaps="post_as_main_image")


    @property
    def url(self):
        # インデントを揃える
        if self.unique_filename:
            return url_for('static', filename=os.path.join(current_app.config['UPLOAD_FOLDER_RELATIVE_PATH'], self.unique_filename).replace('\\', '/'))
        # else に続くか、if ブロックと同じインデントレベルにする
        return None # unique_filename がない場合はURLを返さない


    @property
    def thumbnail_url(self):
        # インデントを揃える
        if self.thumbnail_filename:
            return url_for('static', filename=os.path.join(current_app.config['THUMBNAIL_FOLDER_RELATIVE_PATH'], self.thumbnail_filename).replace('\\', '/'))
        # else に続くか、if ブロックと同じインデントレベルにする
        return self.url if self.unique_filename else url_for('static', filename='images/default_thumbnail.png')

    def __repr__(self):
        return f"<Image '{self.original_filename}' ({self.unique_filename})>"

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

    user_id = db.Column(UUIDType(binary=False), db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(UUIDType(binary=False), db.ForeignKey('category.id'), nullable=True)
    main_image_id = db.Column(UUIDType(binary=False), db.ForeignKey('image.id'), unique=True, nullable=True) 

    # リレーションシップ
    posted_by = relationship('User', back_populates='posts')
    category = relationship('Category', back_populates='posts')
    main_image = relationship(
        'Image', 
        backref=db.backref('post_as_main_image', uselist=False),
        foreign_keys=[main_image_id],
        overlaps="main_image_for_post",
        post_update=True
    )
    images = relationship(
        'Image',
        primaryjoin="Post.id == Image.post_id",
        back_populates='post',
        foreign_keys=[Image.post_id],
        cascade='all, delete-orphan'
    )
    tags = relationship('Tag', secondary=post_tags, backref=db.backref('posts', lazy='dynamic'))
    additional_images = relationship(
        'Image',
        secondary=post_additional_images,
        backref=db.backref('posts_as_additional_image', lazy='dynamic')
    )
    
    # ★★★ 修正点 2 ★★★
    # back_populates を追加し、Comment.post との双方向関係を明示
    comments = relationship('Comment', back_populates='post', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Post {self.title}>'
        
class Comment(db.Model):
    """
    ユーザーがブログ投稿に対して行ったコメントを表します。
    """
    __tablename__ = 'comment'
    id = db.Column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc), onupdate=lambda: datetime.now(pytz.utc), nullable=False)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)

    user_id = db.Column(UUIDType(binary=False), db.ForeignKey('user.id'), nullable=False) 
    post_id = db.Column(UUIDType(binary=False), db.ForeignKey('post.id'), nullable=False) 
    author_name = db.Column(db.String(64), nullable=False)  # ←この行を追加

    # ★★★ 修正点 3 ★★★
    # 競合していた 'user' relationship を削除し、'comment_author' と 'post' に
    # back_populates を設定して双方向関係を確立
    comment_author = relationship('User', back_populates='comments')
    post = relationship('Post', back_populates='comments')
    
    def __repr__(self):
        return f'<Comment {self.id} on Post {self.post_id}>'
    
class QR(db.Model):
    __tablename__ = 'qr_codes' # テーブル名を指定する
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    qr_image_filename = db.Column(db.String(255), nullable=False) # 生成されたQRコード画像のファイル名
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"QR(id='{self.id}', name='{self.name}', url='{self.url}')"