from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField, IntegerField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from flask_login import current_user
from models import User

class RegistrationForm(FlaskForm):
    username = StringField('მომხმარებლის სახელი', validators=[
        DataRequired(message='ეს ველი სავალდებულოა'),
        Length(min=4, max=50, message='სახელი უნდა იყოს 4-50 სიმბოლო')
    ])
    email = StringField('ელ. ფოსტა', validators=[
        DataRequired(message='ეს ველი სავალდებულოა'),
        Email(message='გთხოვთ შეიყვანოთ სწორი ელ. ფოსტა')
    ])
    password = PasswordField('პაროლი', validators=[
        DataRequired(message='ეს ველი სავალდებულოა'),
        Length(min=8, message='პაროლი უნდა შედგებოდეს მინიმუმ 8 სიმბოლოსგან')
    ])
    confirm_password = PasswordField('პაროლის დადასტურება', validators=[
        DataRequired(message='ეს ველი სავალდებულოა'),
        EqualTo('password', message='პაროლები უნდა ემთხვეოდეს ერთმანეთს')
    ])
    submit = SubmitField('რეგისტრაცია')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('ეს სახელი უკვე გამოყენებულია')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('ეს ელ.ფოსტა უკვე რეგისტრირებულია')

class LoginForm(FlaskForm):
    email = StringField('ელ. ფოსტა', validators=[
        DataRequired(message='ეს ველი სავალდებულოა'),
        Email(message='გთხოვთ შეიყვანოთ სწორი ელ. ფოსტა')
    ])
    password = PasswordField('პაროლი', validators=[
        DataRequired(message='ეს ველი სავალდებულოა')
    ])
    remember = BooleanField('დამიმახსოვრე')
    submit = SubmitField('შესვლა')

class TwoFactorForm(FlaskForm):
    token = StringField('ავთენტიფიკაციის კოდი', validators=[
        DataRequired(message='ეს ველი სავალდებულოა'),
        Length(min=6, max=6, message='კოდი უნდა შედგებოდეს 6 ციფრისგან')
    ])
    submit = SubmitField('დადასტურება')

class ProfileForm(FlaskForm):
    username = StringField('მომხმარებლის სახელი', validators=[
        DataRequired(message='ეს ველი სავალდებულოა'),
        Length(min=4, max=50, message='სახელი უნდა იყოს 4-50 სიმბოლო'),
    ])
    email = StringField('ელ. ფოსტა', validators=[
        DataRequired(message='ეს ველი სავალდებულოა'),
        Email(message='გთხოვთ შეიყვანოთ სწორი ელ. ფოსტა')
    ])
    bio = TextAreaField('ბიოგრაფია', validators=[Length(max=500)
    ])
    avatar = FileField('პროფილის სურათი')
    current_password = PasswordField('მიმდინარე პაროლი', validators=[
        DataRequired(message='ეს ველი სავალდებულოა')
    ])
    submit = SubmitField('განახლება')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('ეს სახელი უკვე გამოყენებულია')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('ეს ელ. ფოსტა უკვე რეგისტრირებულია')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('მიმდინარე პაროლი', validators=[
        DataRequired(message='ეს ველი სავალდებულოა')
    ])
    new_password = PasswordField('ახალი პაროლი', validators=[
        DataRequired(message='ეს ველი სავალდებულოა'),
        Length(min=8, message='პაროლი უნდა შედგებოდეს მინიმუმ 8 სიმბოლოსგან')
    ])
    confirm_password = PasswordField('ახალი პაროლის დადასტურება', validators=[
        DataRequired(message='ეს ველი სავალდებულოა'),
        EqualTo('new_password', message='პაროლები უნდა ემთხვეოდეს ერთმანეთს')
    ])
    submit = SubmitField('პაროლის შეცვლა')


class GameForm(FlaskForm):
    title = StringField('სათაური', validators=[
        DataRequired(message='ეს ველი სავალდებულოა'),
        Length(max=100, message='სათაური უნდა იყოს მაქსიმუმ 100 სიმბოლო')
    ])
    short_description = StringField('მოკლე აღწერა', validators=[
        DataRequired(message='ეს ველი სავალდებულოა'),
        Length(max=200, message='მოკლე აღწერა უნდა იყოს მაქსიმუმ 200 სიმბოლო')
    ])
    description = TextAreaField('სრული აღწერა', validators=[
        DataRequired(message='ეს ველი სავალდებულოა')
    ])
    cover_image = FileField('ფოტო', validators=[
        DataRequired(message='ეს ველი სავალდებულოა')
    ])
    download_link = StringField('გადმოწერის ლინკი', validators=[
        DataRequired(message='ეს ველი სავალდებულოა'),
        Length(max=256, message='ლინკი უნდა იყოს მაქსიმუმ 256 სიმბოლო')
    ])
    version = StringField('ვერსია', validators=[
        Length(max=20, message='ვერსია უნდა იყოს მაქსიმუმ 20 სიმბოლო')
    ])
    is_free = BooleanField('უფასო თამაში')
    cost = IntegerField('ფასი (₾)', default=0)
    submit = SubmitField('გამოქვეყნება')

    def validate_cost(self, field):
        if not self.is_free.data and (field.data is None or field.data <= 0):
            raise ValidationError('გთხოვთ მიუთითეთ ფასი, თუ თამაში არ არის უფასო')
class RatingForm(FlaskForm):
    score = IntegerField('რეიტინგი (1-5)', validators=[
        DataRequired(message='ეს ველი სავალდებულოა')
    ])
    review = TextAreaField('რეცენზია')
    submit = SubmitField('შეფასების დამატება')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message='ეს ველი სავალდებულოა'),
        Email(message='გთხოვთ შეიყვანოთ სწორი ელ. ფოსტა')
    ])
    submit = SubmitField('Send Reset Link')

class DummyForm(FlaskForm):
    pass

class ResetPasswordForm(FlaskForm):
    new_password = PasswordField('ახალი პაროლი', validators=[
        DataRequired(message='ეს ველი სავალდებულოა'),
        Length(min=8, message='პაროლი უნდა შედგებოდეს მინიმუმ 8 სიმბოლოსგან')
    ])
    confirm_password = PasswordField('ახალი პაროლის დადასტურება', validators=[
        DataRequired(message='ეს ველი სავალდებულოა'),
        EqualTo('new_password', message='პაროლები უნდა ემთხვეოდეს ერთმანეთს')
    ])
    submit = SubmitField('პაროლის შეცვლა')
