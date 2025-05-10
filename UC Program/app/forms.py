from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, PasswordField, SubmitField, BooleanField, IntegerField, FloatField
from wtforms.validators import InputRequired, Length, ValidationError


class Register(FlaskForm):
    name = StringField(validators=[InputRequired(), Length(max=30)])
    username = StringField(validators=[InputRequired(), Length(max=25)])
    email = StringField(validators=[InputRequired(), Length(max=254)])    
    password = PasswordField(validators=[InputRequired(), Length(max=50)])
    confirm_password = PasswordField(validators=[InputRequired(), Length(max=50)])
    recaptcha = RecaptchaField()
    submit = SubmitField("Register")


class Login(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(max=25)])
    
    password = PasswordField(validators=[InputRequired(), Length(max=50)])
    
    remember_me = BooleanField(default=False)
    
    submit = SubmitField("Login")

class Single_Event(FlaskForm):
    Area = FloatField(validators=[InputRequired()])
    ADD = FloatField(validators=[InputRequired()])
    INT = FloatField(validators=[InputRequired()])
    DUR = FloatField(validators=[InputRequired()])
    pH = FloatField(validators=[InputRequired()])

    submit = SubmitField("Submit")

