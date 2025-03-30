from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError


class Register(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(max=25)])
    email = StringField(validators=[InputRequired(), Length(max=254)])    
    password = PasswordField(validators=[InputRequired(), Length(max=50)])
    confirm_password = PasswordField(validators=[InputRequired(), Length(max=50)])
    
    submit = SubmitField("Register")


class Login(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(
         max=25)], render_kw={"placeholder": "Username"})
    
    password = PasswordField(validators=[InputRequired(), Length(
        max=50)], render_kw={"placeholder": "Password"})
    
    submit = SubmitField("Login")