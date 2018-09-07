from wtforms import Form, BooleanField, StringField, PasswordField, validators,TextAreaField
class register_form(Form):
    zid = StringField('zid', [validators.Length(min=4, max=25),validators.required()])
    fullname = StringField('fullname', [validators.required()])
    mail = StringField('mail', [validators.email(),validators.required()])
    password = PasswordField('password',[validators.EqualTo('password2',message='Passwords must match'),validators.required()])
    password2 = PasswordField('password2',[validators.required()])
    suburb = StringField('suburb')
    program = StringField('program')
    birthday = StringField('birthday')
    longitude = StringField('longitude')
    latitude = StringField('latitude')
    courses = StringField('courses')


class forget_pass_form(Form):
    zid = StringField('zid', [validators.Length(min=4, max=25),validators.required()])
    mail = StringField('mail', [validators.email(),validators.required()])

class new_pass_form(Form):
    password = PasswordField('password',[validators.EqualTo('password2',message='Passwords must match'),validators.required()])
    password2 = PasswordField('password2',[validators.required()])

class edit_user_info_form(Form):
    fullname = StringField('fullname', [validators.required()])
    mail = StringField('mail', [validators.email(),validators.required()])
    suburb = StringField('suburb')
    program = StringField('program')
    birthday = StringField('birthday')
    longitude = StringField('longitude')
    latitude = StringField('latitude')
    courses = StringField('courses')
    profile = TextAreaField('profile')
