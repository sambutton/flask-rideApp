
from flask_wtf import FlaskForm
from flask_babel import gettext
import wtforms
from wtforms import StringField, BooleanField, TextAreaField, PasswordField, DateField, SelectField, HiddenField
from wtforms.validators import DataRequired, Length, Required
from wtforms.fields.html5 import EmailField
from flask_wtf.file import FileField, FileRequired, FileAllowed
from werkzeug.utils import secure_filename
from flask_admin.form.fields import TimeField
from flask_admin.form import widgets, DatePickerWidget
#from .fieldwidgets import DatePickerWidget
from .models import User


class LoginForm(FlaskForm):
    email = EmailField('email', validators=[DataRequired(), wtforms.validators.Email("Please enter your email address.")])
    password = PasswordField('password', validators=[DataRequired()])
    remember_me = BooleanField('remember_me', default=False)

class SignUpForm(FlaskForm):
    name = StringField('name', validators=[DataRequired()])
    email = EmailField('email', validators=[DataRequired(), wtforms.validators.Email("Please enter your email address.")])
    password = PasswordField('password', validators=[DataRequired()])
    address = StringField('address', validators=[DataRequired()])
    city = StringField('city', validators=[DataRequired()])
    state = StringField('state', validators=[DataRequired()])
    zipcode = StringField('zipcode', validators=[DataRequired()])
    remember_me = BooleanField('remember_me', default=False)

    #def validate_email(form, field):
    #    if field.data < 13:
    #        raise ValidationError("We're sorry, you must be 13 or older to register")
    
class EditForm(FlaskForm):
    nickname = StringField('nickname', validators=[DataRequired()])
    about_me = TextAreaField('about_me', validators=[Length(min=0, max=140)])
    email = EmailField('email')
    #password = PasswordField('password', validators=[DataRequired()])
    address = StringField('address')
    city = StringField('city')
    state = StringField('state')
    zipcode = StringField('zipcode')
    photo = FileField('photo', validators=[FileAllowed(['jpg', 'png'], 'Images only!')])
    avatar_url = HiddenField('avatar_url')


    def __init__(self, original_nickname, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        self.original_nickname = original_nickname

    def validate(self):
        if not FlaskForm.validate(self):
            return False
        if self.nickname.data == self.original_nickname:
            return True
        if self.nickname.data != User.make_valid_nickname(self.nickname.data):
            self.nickname.errors.append(gettext(
                'This nickname has invalid characters. '
                'Please use letters, numbers, dots and underscores only.'))
            return False
        user = User.query.filter_by(nickname=self.nickname.data).first()
        if user is not None:
            self.nickname.errors.append(gettext(
                'This nickname is already in use. '
                'Please choose another one.'))
            return False
        return True


class PostForm(FlaskForm):
    destination = StringField('destination', validators=[DataRequired("Please tell us where you are going.")])
    trip_date = DateField('TripDate', validators=[Required()], format = '%m/%d/%Y')
    trip_time = TimeField('TripTime', validators=[Required()])
    needRide = SelectField('needRide', validators=[Required()], choices=[('Need a ride','Need a ride'), ('Offering a ride','Offering a ride')], option_widget=None)
    seats = SelectField('seats', validators=[Required()], choices=[(1,'1'),(2,'2'),(3,'3'),(4,'4'),(5,'5')], coerce=int, option_widget=None)
    body = TextAreaField('body', validators=[DataRequired("Please tell us something about your trip."), Length(max=140)])


class SearchForm(FlaskForm):
    search = StringField('search', validators=[DataRequired()])

