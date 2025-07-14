from extensions import mail
from flask_mail import Message
from flask import current_app, url_for
import os
import random
from PIL import Image
import secrets

def save_picture(file, folder):
    random_hex = secrets.token_hex(8)
    _, ext = os.path.splitext(file.filename)
    new_filename = random_hex + ext.lower()
    # _, ext = os.path.splitext(filename)
    random_hex = os.urandom(8).hex()
    new_filename = random_hex + ext.lower()
    
    save_path = os.path.join(current_app.root_path, 'static', 'uploads', folder)
    os.makedirs(save_path, exist_ok=True)
    file_path = os.path.join(save_path, new_filename)

    if folder == 'avatars':
        output_size = (300, 300)
        img = Image.open(file)
        img.thumbnail(output_size)
        img.save(file_path)
    else:
        file.save(file_path)
    
    return new_filename

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('პაროლის აღდგენის მოთხოვნა',
                  sender=current_app.config['MAIL_DEFAULT_SENDER'],
                  recipients=[user.email])
    msg.body = f'''პაროლის აღსადგენად გთხოვთ გადახვიდეთ შემდეგ ლინკზე:
{url_for('main.reset_password', token=token, _external=True)}

თუ თქვენ არ გაგიგზავნიათ ეს მოთხოვნა, გთხოვთ უგულებელყოთ ეს წერილი.
'''
    mail.send(msg)


def generate_verification_code():
    return str(random.randint(100000, 999999))

def send_verification_email(user, code):
    msg = Message('ელ. ფოსტის დადასტურება', recipients=[user.email])
    msg.sender = current_app.config['MAIL_DEFAULT_SENDER']
    msg.body = f'''
გამარჯობა, {user.username}!
თქვენი ანგარიშის დადასტურების კოდია: {code}

თუ თქვენ არ შექმენით ეს ანგარიში, გთხოვთ უგულებელყოთ ეს წერილი.
'''
    mail.send(msg)
