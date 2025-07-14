import os
from dotenv import load_dotenv
from app import create_app
from extensions import db, bcrypt
from models import User, Game, Rating, DeveloperRequest

load_dotenv()

def create_user(username, email, password, **kwargs):
    if not User.query.filter_by(email=email).first():
        user = User(
            username=username,
            email=email,
            password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
            **kwargs
        )
        db.session.add(user)

def create_admin_and_moderators():
    owners = [
        {
            "username": os.getenv("OWNER1_USERNAME"),
            "email": os.getenv("OWNER1_EMAIL"),
            "password": os.getenv("OWNER1_PASSWORD")
        },
        {
            "username": os.getenv("OWNER2_USERNAME"),
            "email": os.getenv("OWNER2_EMAIL"),
            "password": os.getenv("OWNER2_PASSWORD")
        }
    ]

    admins = [
        {
            "username": os.getenv("ADMIN1_USERNAME"),
            "email": os.getenv("ADMIN1_EMAIL"),
            "password": os.getenv("ADMIN1_PASSWORD")
        },
        {
            "username": os.getenv("ADMIN2_USERNAME"),
            "email": os.getenv("ADMIN2_EMAIL"),
            "password": os.getenv("ADMIN2_PASSWORD")
        },
        {
            "username": os.getenv("ADMIN3_USERNAME"),
            "email": os.getenv("ADMIN3_EMAIL"),
            "password": os.getenv("ADMIN3_PASSWORD")
        }
    ]

    moderators = [
        {
            "username": os.getenv("MODERATOR1_USERNAME"),
            "email": os.getenv("MODERATOR1_EMAIL"),
            "password": os.getenv("MODERATOR1_PASSWORD")
        },
        {
            "username": os.getenv("MODERATOR2_USERNAME"),
            "email": os.getenv("MODERATOR2_EMAIL"),
            "password": os.getenv("MODERATOR2_PASSWORD")
        },
        {
            "username": os.getenv("MODERATOR3_USERNAME"),
            "email": os.getenv("MODERATOR3_EMAIL"),
            "password": os.getenv("MODERATOR3_PASSWORD")
        }
    ]

    for owner in owners:
        create_user(owner["username"], owner["email"], owner["password"],
                    is_Owner=True, is_admin=True, is_moderator=True, is_developer=True, is_verified=True)

    for admin in admins:
        create_user(admin["username"], admin["email"], admin["password"],
                    is_admin=True, is_moderator=True, is_developer=True, is_verified=True)

    for moderator in moderators:
        create_user(moderator["username"], moderator["email"], moderator["password"],
                    is_moderator=True, is_verified=True)

    db.session.commit()

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        print("ბაზის ცხრილები შეიქმნა")

        create_admin_and_moderators()
        print("ადმინები და მოდერატორები დაემატა")
