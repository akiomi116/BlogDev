# F:\dev\BrogDev\app\forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, BooleanField, FileField, SelectField, MultipleFileField, SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional
from flask_wtf.file import FileAllowed, FileRequired
from app.models import User, Category, Role, Tag 
from flask_login import current_user # current_user をインポート
import logging # ロギングをインポート

logger = logging.getLogger(__name__) # ロガーを設定

# 認証フォーム (ログイン・登録兼用)
class AuthForm(FlaskForm):
    username = StringField('ユーザー名', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('パスワード（確認）', validators=[DataRequired(), EqualTo('password', message='パスワードが一致しません')])
    submit = SubmitField('登録')

    # ユーザー名の一意性バリデーション
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('このユーザー名は既に使われています。')

    # メールアドレスの一意性バリデーション
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('このメールアドレスは既に登録されています。')

class LoginForm(FlaskForm):
    username = StringField('ユーザー名', validators=[DataRequired()])
    password = PasswordField('パスワード', validators=[DataRequired()])
    remember_me = BooleanField('ログイン情報を記憶する')
    submit = SubmitField('ログイン')

# ユーザー管理フォーム
class UserForm(FlaskForm):
    username = StringField('ユーザー名', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード', validators=[Optional(), Length(min=6)], description='変更する場合のみ入力')
    confirm_password = PasswordField('パスワード（確認）', validators=[EqualTo('password', message='パスワードが一致しません')])
    
    role_id = SelectField('ロール', coerce=str, validators=[DataRequired()])
    submit = SubmitField('更新')

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        # ここでRoleモデルをローカルにインポートすることで循環参照を避ける
        from app.models import Role 
        self.role_id.choices = [(str(role.id), role.name) for role in Role.query.all()]

    def validate_username(self, username):
        from app.models import User # ここでもUserモデルをローカルにインポート
        if self.obj and username.data == self.obj.username:
            return 
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('そのユーザー名は既に使われています。別のユーザー名を選んでください。')

    def validate_email(self, email):
        from app.models import User # ここでもUserモデルをローカルにインポート
        if self.obj and email.data == self.obj.email:
            return 
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('そのメールアドレスは既に登録されています。')

class AddUserForm(FlaskForm):
    username = StringField('ユーザー名', validators=[DataRequired()])
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード', validators=[DataRequired()])
    confirm_password = PasswordField('パスワード確認', validators=[DataRequired(), EqualTo('password', message='パスワードが一致しません。')])
    role = SelectField('ロール', coerce=int, validators=[DataRequired()])
    submit = SubmitField('ユーザー作成')

    def __init__(self, *args, **kwargs):
        super(AddUserForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name) for role in Role.query.order_by(Role.name).all()]

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('そのユーザー名はすでに使用されています。別のユーザー名を選択してください。')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('そのメールアドレスはすでに使用されています。別のメールアドレスを選択してください。')

class EditUserForm(FlaskForm):
    username = StringField('ユーザー名', validators=[DataRequired()])
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    role = SelectField('ロール', coerce=int, validators=[DataRequired()])
    # パスワードはオプションにすることが多い。ユーザーが変更したい場合のみ入力する
    password = PasswordField('新しいパスワード', validators=[Optional()]) # Optional を使用
    confirm_password = PasswordField('新しいパスワード確認', validators=[Optional(), EqualTo('password', message='パスワードが一致しません。')])
    submit = SubmitField('ユーザー更新')

    def __init__(self, original_username, original_email, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email
        self.role.choices = [(role.id, role.name) for role in Role.query.order_by(Role.name).all()]

    def validate_username(self, username):
        # ユーザー名が変更され、かつ既存のユーザー名と重複する場合
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user:
                raise ValidationError('そのユーザー名はすでに使用されています。別のユーザー名を選択してください。')

    def validate_email(self, email):
        # メールアドレスが変更され、かつ既存のメールアドレスと重複する場合
        if email.data != self.original_email:
            user = User.query.filter_by(email=self.email.data).first()
            if user:
                raise ValidationError('そのメールアドレスはすでに使用されています。別のメールアドレスを選択してください。')

# ロール管理フォーム
class RoleForm(FlaskForm):
    name = StringField('ロール名', validators=[DataRequired(), Length(max=50)])
    submit = SubmitField('保存')

    def validate_name(self, name):
        role = Role.query.filter_by(name=name.data).first()
        if role and not self.obj or (self.obj and self.obj.name != name.data): # 編集時は自分自身の名前は許容
            raise ValidationError('このロール名は既に存在します。')

class ChangeUserRoleForm(FlaskForm):
    role = SelectField('新しいロール', coerce=int, validators=[DataRequired()])
    submit = SubmitField('ロール更新')

    def __init__(self, *args, **kwargs):
        super(ChangeUserRoleForm, self).__init__(*args, **kwargs)
        # データベースから利用可能なロールを取得し、SelectField の選択肢として設定
        self.role.choices = [(role.id, role.name) for role in Role.query.order_by(Role.name).all()]

# カテゴリ管理フォーム
class CategoryForm(FlaskForm):
    name = StringField('カテゴリ名', validators=[DataRequired(), Length(min=2, max=100)])
    slug = StringField('スラッグ', validators=[Optional(), Length(min=2, max=100)])
    description = TextAreaField('説明', validators=[Length(max=500)])
    submit = SubmitField('保存')
 
    def validate_name(self, name):
        # 新規作成時と編集時で異なるロジック
        if not hasattr(self, 'obj') or self.obj is None:  # 新規作成時
            category = Category.query.filter_by(name=name.data).first()
            if category:
                raise ValidationError('このカテゴリ名は既に存在します。')
        else:  # 編集時
            # 既存のカテゴリと名前が同じで、かつそれが現在のカテゴリではない場合
            category = Category.query.filter_by(name=name.data).first()
            if category and category.id != self.obj.id:
                raise ValidationError('このカテゴリ名は既に存在します。')

    def validate_slug(self, slug):
        # 新規作成時と編集時で異なるロジック
        if not hasattr(self, 'obj') or self.obj is None:  # 新規作成時
            category = Category.query.filter_by(slug=slug.data).first()
            if category:
                raise ValidationError('このスラッグは既に存在します。')
        else:  # 編集時
            category = Category.query.filter_by(slug=slug.data).first()
            if category and category.id != self.obj.id:
                raise ValidationError('このスラッグは既に存在します。')


# タグ管理フォーム
class TagForm(FlaskForm):
    name = StringField('タグ名', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('保存')

    def validate_name(self, name):
        # 新規作成時と編集時で異なるロジック
        if not hasattr(self, 'obj') or self.obj is None:  # 新規作成時
            tag = Tag.query.filter_by(name=name.data).first()
            if tag:
                raise ValidationError('このタグ名は既に存在します。')
        else:  # 編集時
            # 既存のタグと名前が同じで、かつそれが現在のタグではない場合
            tag = Tag.query.filter_by(name=name.data).first()
            if tag and tag.id != self.obj.id:  # IDで比較して自分自身を除外
                raise ValidationError('このタグ名は既に存在します。')


# 画像アップロードフォーム
# 単一ファイルアップロード用
class ImageUploadForm(FlaskForm):
    image_file = FileField('画像ファイル', validators=[
        FileRequired('ファイルを選択してください。'),
        FileAllowed(['jpg', 'png', 'jpeg', 'gif'], '画像ファイル (jpg, png, jpeg, gif) のみアップロード可能です。')
    ])
    submit = SubmitField('アップロード') 

class BulkImageUploadForm(FlaskForm):
    # FileFieldはWTFormsのFileFieldとは異なり、Flask-WTFのFileFieldを使う
    # multiple=True を設定することで複数ファイル選択を可能にする
    files = FileField('画像ファイルを選択', validators=[
        FileRequired('ファイルを１つ以上選択してください。'),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], '画像ファイル (JPG, JPEG, PNG, GIF) のみをアップロードできます。')
    ], render_kw={"multiple": True}) # HTMLのmultiple属性を付与
    submit = SubmitField('アップロード')


class CommentForm(FlaskForm):
    #author_name = StringField('名前', validators=[DataRequired(), Length(min=2, max=50)])
    #email = StringField('メールアドレス (非公開)', validators=[DataRequired(), Email()]) # 追加
    content = TextAreaField('コメント', validators=[DataRequired(), Length(min=1, max=1000)])
    submit = SubmitField('コメントを送信')
