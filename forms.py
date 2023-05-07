from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    username = StringField(label='Логин:', validators=[DataRequired()])
    password = PasswordField(label='Пароль:', validators=[DataRequired()])
    submit = SubmitField(label='Войти')
