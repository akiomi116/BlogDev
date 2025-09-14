# F:\dev\BrogDev\app\forms.py

from flask_wtf import FlaskForm
from flask_wtf.file import  MultipleFileField, FileAllowed, FileRequired, FileField
from wtforms import StringField, TextAreaField, BooleanField, SubmitField, PasswordField, SelectField, SelectMultipleField,HiddenField
from wtforms.fields import EmailField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from app.extensions import db
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
import os

import uuid  # UUIDTypeField のデフォルト値として uuid.uuid4 を使う場合に必要
from app.models import Category, Tag, Image, User, Role  # Role モデルをインポート

class DeleteForm(FlaskForm):
    """汎用的な削除確認フォーム（CSRFトークンのみ）"""
    submit = SubmitField('削除')

class LoginForm(FlaskForm):
    """ログインフォーム"""
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード', validators=[DataRequired(), Length(min=6)])
    remember_me = BooleanField('ログイン状態を保持する')
    submit = SubmitField('ログイン')

class RegistrationForm(FlaskForm):
    """ユーザー登録フォーム"""
    username = StringField('ユーザー名', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('パスワードの確認', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('登録')

    def validate_username(self, username):
        print("validate_username called")
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            print("User found in validate_username")
            raise ValidationError('そのユーザー名はすでに使われています。')
            print(f"Expected error message bytes: {'そのユーザー名はすでに使われています。'.encode('utf-8')}")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('そのメールアドレスはすでに登録されています。')

class ChangePasswordForm(FlaskForm):
    """パスワード変更フォーム"""
    old_password = PasswordField('現在のパスワード', validators=[DataRequired()])
    new_password = PasswordField('新しいパスワード', validators=[DataRequired(), Length(min=6)])
    new_password2 = PasswordField(
        '新しいパスワード再入力', validators=[DataRequired(), EqualTo('new_password', message='パスワードが一致しません。')])
    submit = SubmitField('パスワードを変更')

class ResetPasswordRequestForm(FlaskForm):
    """パスワードリセット要求フォーム"""
    email = EmailField('メールアドレス', validators=[DataRequired(), Email()])
    submit = SubmitField('パスワードをリセット')

class ResetPasswordForm(FlaskForm):
    """パスワードリセットフォーム"""
    password = PasswordField('新しいパスワード', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        '新しいパスワード再入力', validators=[DataRequired(), EqualTo('password', message='パスワードが一致しません。')])
    submit = SubmitField('パスワードをリセット')

class PostForm(FlaskForm):
    """投稿作成・編集フォーム"""
    title = StringField('タイトル', validators=[DataRequired(), Length(min=1, max=255)])
    body = TextAreaField('本文', validators=[DataRequired()])
    
    # メイン画像用のファイルアップロードフィールド
    main_image_file = FileField('メイン画像アップロード', validators=[Optional()
        #FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], '画像ファイル (JPG, JPEG, PNG, GIF, WEBP) のみ許可されます')
    ])
    
    selected_image_id = HiddenField('選択画像ID')
    
    
    # 既存のメイン画像を選択するためのフィールド (IDをhiddenで送る想定)
    main_image = QuerySelectField(
        'または既存のメイン画像を選択',
        query_factory=lambda: Image.query.order_by(Image.original_filename).all(),
        get_pk=lambda a: str(a.id), 
        get_label=lambda a: a.original_filename, 
        allow_blank=True, 
        blank_text='--- 選択してください ---',
        validators=[Optional()] 
    )
    
    main_image_alt_text = StringField('メイン画像の代替テキスト (Alt Text)', validators=[Optional(), Length(max=255)])

    # 複数の追加画像を選択するためのフィールド
    additional_images = QuerySelectMultipleField(
        '追加画像を選択 (複数選択可)',
        query_factory=lambda: Image.query.order_by(Image.original_filename).all(),
        get_pk=lambda a: str(a.id),
        get_label=lambda a: a.original_filename,
        allow_blank=True,
        validators=[Optional()]
    )

    # カテゴリ選択フィールド
    category = SelectField(
        'カテゴリ',
        coerce=str,  # UUIDならstr、intならint
        validators=[Optional()]
    )
    
    # タグ選択フィールド（複数選択可）
    tags = QuerySelectMultipleField(
        'タグ',
        query_factory=lambda: Tag.query.order_by(Tag.name).all(),
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=True,
        validators=[Optional()]
    )

    is_published = BooleanField('公開する')
    submit = SubmitField('投稿を作成')

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.obj = kwargs.get('obj')

    
    def validate(self, extra_validators=None):
        rv = super(PostForm, self).validate(extra_validators=extra_validators)
        if not rv:
            return False
        
        # 新規投稿の場合(self.obj is None)、メイン画像は必須
        if not self.obj:
            file_data = self.main_image_file.data
            has_upload = False
            
            if file_data and file_data.filename:
                # content_length is unreliable, so check the stream size directly.
                # Move to the end of the stream to get its size.
                file_data.stream.seek(0, os.SEEK_END) 
                file_size = file_data.stream.tell()
                # IMPORTANT: Reset stream position for further processing
                file_data.stream.seek(0) 
                has_upload = file_size > 0

            has_gallery_selection = self.selected_image_id.data

            if not (has_upload or has_gallery_selection):
                msg = 'メイン画像は必須です。ファイルをアップロードするか、ギャラリーから選択してください。'
                self.main_image_file.errors.append(msg)
                return False
        return True

class ImageUploadForm(FlaskForm):
    """単一画像アップロードフォーム（Alt Text付き）"""
    image = FileField('画像ファイル', validators=[
        FileRequired('画像ファイルを選択してください。'),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], '画像ファイル (JPG, JPEG, PNG, GIF, WEBP) のみ許可されます')
    ])
    alt_text = StringField('代替テキスト (Alt Text)', validators=[Optional(), Length(max=255)])
    submit = SubmitField('アップロード')

class BulkImageUploadForm(FlaskForm):
    """複数画像一括アップロードフォーム"""
    images = MultipleFileField('画像ファイル (複数選択可)', validators=[
        FileRequired('画像ファイルを選択してください。'),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], '画像ファイル (JPG, JPEG, PNG, GIF, WEBP) のみ許可されます')
    ])
    submit = SubmitField('一括アップロード')

class CategoryForm(FlaskForm):
    """カテゴリ作成・編集フォーム"""
    name = StringField('カテゴリ名', validators=[DataRequired()])
    description = TextAreaField('説明', validators=[Optional()])
    submit = SubmitField('保存')

    def validate_name(self, name):
        pass 

class TagForm(FlaskForm):
    """タグ作成・編集フォーム"""
    name = StringField('タグ名', validators=[DataRequired(), Length(min=1, max=50)])
    submit = SubmitField('保存')

    def validate_name(self, name):
        pass

class CommentAdminEditForm(FlaskForm):
    """コメント編集フォーム (管理者用)"""
    body = TextAreaField('内容', validators=[DataRequired()])
    is_approved = BooleanField('承認済み')
    submit = SubmitField('更新')


class CommentForm(FlaskForm):
    """コメントフォーム"""
    author_name = StringField('名前', validators=[Optional()])
    body = TextAreaField('コメント', validators=[DataRequired()])
    submit = SubmitField('コメントを送信')

class UserEditForm(FlaskForm):
    """ユーザー情報編集フォーム (管理者用)"""
    username = StringField('ユーザー名', validators=[DataRequired(), Length(min=3, max=64)])
    email = EmailField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('新しいパスワード', validators=[Optional(), Length(min=6)], description='変更しない場合は空のままにしてください。')
    is_active = BooleanField('アカウントをアクティブにする')
    
    # ロール選択フィールド (複数選択可)
    roles = QuerySelectMultipleField(
        'ロール',
        query_factory=lambda: Role.query.order_by(Role.name).all(),
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=True,
        validators=[Optional()]
    )
    submit = SubmitField('ユーザー情報を更新')

    # メールアドレスの重複チェック (編集時、自分自身は除く)
    # obj=user でインスタンス化される場合、WTForms は通常 __init__ に obj を渡す
    # ただし、original_email を明示的に渡す場合は以下のようにする
    def __init__(self, original_email=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # original_email が渡されなかった場合は、obj から初期値を設定する（編集時）
        # 新規作成フォームとしてUserEditFormを使わない限り、これは常に設定される
        if original_email is None and kwargs.get('obj'):
            self.original_email = kwargs['obj'].email
        else:
            self.original_email = original_email

    def validate_email(self, email):
        # フォームにデータがロードされている場合のみチェックを実行
        # (新規フォームと編集フォームで挙動を調整する必要がある場合)
        if email.data and email.data != self.original_email:
            user = User.query.filter_by(email=self.email.data).first()
            if user is not None:
                raise ValidationError('そのメールアドレスはすでに登録されています。')

