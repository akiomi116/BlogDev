# F:\dev\BrogDev\app\forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, Optional
from app.models import User # validate_username/email でUserモデルが必要

# ログインフォーム
class LoginForm(FlaskForm):
    username = StringField('ユーザー名', validators=[DataRequired()])
    password = PasswordField('パスワード', validators=[DataRequired()])
    remember_me = BooleanField('ログイン情報を記憶する')
    submit = SubmitField('ログイン')

# 認証フォーム (新規登録など汎用的な認証操作用)
class AuthForm(FlaskForm):
    username = StringField('ユーザー名', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        'パスワードの確認', validators=[DataRequired(), EqualTo('password', message='パスワードが一致しません。')]
    )
    submit = SubmitField('登録')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('そのユーザー名はすでに使われています。別のユーザー名を選んでください。')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('そのメールアドレスはすでに登録されています。')

# パスワードリセットリクエストフォーム
class RequestResetForm(FlaskForm):
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    submit = SubmitField('パスワードリセットをリクエスト')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('そのメールアドレスを持つアカウントはありません。登録してください。')

# パスワードリセットフォーム
class ResetPasswordForm(FlaskForm):
    password = PasswordField('新しいパスワード', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        'パスワードの確認', validators=[DataRequired(), EqualTo('password', message='パスワードが一致しません。')]
    )
    submit = SubmitField('パスワードをリセット')

# コメントフォーム (一般ユーザーがブログ記事にコメントを投稿するためのもの)
class CommentForm(FlaskForm):
    body = TextAreaField('コメント本文', validators=[DataRequired()])
    submit = SubmitField('コメントを送信')

# CSRF保護のみを目的としたシンプルなフォーム
class CsrfOnlyForm(FlaskForm):
    pass

# お問い合わせフォーム (一般ユーザーが使用)
class ContactForm(FlaskForm):
    name = StringField('名前', validators=[DataRequired(), Length(max=100)])
    email = StringField('メールアドレス', validators=[DataRequired(), Email(), Length(max=120)])
    subject = StringField('件名', validators=[DataRequired(), Length(max=200)])
    message = TextAreaField('メッセージ', validators=[DataRequired()])
    submit = SubmitField('送信')

# もしQRコード生成が一般ユーザー向け機能なら、ここに配置
# class QRForm(FlaskForm):
#     name = StringField('QRコード名', validators=[DataRequired(), Length(min=1, max=100)])
#     url = StringField('URL', validators=[DataRequired(), Length(min=1, max=500)])
#     submit = SubmitField('QRコードを作成/更新')