from datetime import datetime
from flask import current_app, url_for
from flask_login import UserMixin
from werkzeug.security import check_password_hash as werkzeug_check
from itsdangerous import BadSignature, SignatureExpired, TimedSerializer as Serializer
from extensions import db, bcrypt
import pyotp

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    avatar = db.Column(db.String(100))
    phone = db.Column(db.String(20), unique=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_developer = db.Column(db.Boolean, default=False)
    is_moderator = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_Owner = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32))
    verification_code = db.Column(db.String(6), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    bio = db.Column(db.Text, nullable=True)
    theme_preference = db.Column(db.String(10), default='light')

    games = db.relationship('Game', backref='developer', lazy='subquery', cascade='all, delete-orphan')
    ratings = db.relationship('Rating', backref='user', lazy='dynamic', cascade='all, delete')

    @property
    def avatar_url(self):
        if self.avatar:
            return url_for('main.get_avatar', filename=self.avatar)
        return url_for('static', filename='images/avatars/default.png')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        if self.password_hash.startswith("$2b$") or self.password_hash.startswith("$2a$"):
            return bcrypt.check_password_hash(self.password_hash, password)
        else:
            return werkzeug_check(self.password_hash, password)

    def verify_account(self):
        if not self.is_verified:
            self.is_verified = True
            db.session.commit()

    def generate_two_factor_secret(self):
        if not self.two_factor_secret:
            self.two_factor_secret = pyotp.random_base32()
            db.session.commit()
        return self.two_factor_secret

    def verify_two_factor_code(self, code):
        totp = pyotp.TOTP(self.two_factor_secret)
        return totp.verify(code)

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}, salt='password-reset')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, salt='password-reset', max_age=1800)['user_id']
            return User.query.get(user_id)
        except (BadSignature, SignatureExpired) as e:
            current_app.logger.warning(f"Invalid reset token: {str(e)}")
            return None

    def promote_to_developer(self):
        if not self.is_developer:
            self.is_developer = True
            db.session.commit()

class Game(db.Model):
    __tablename__ = 'games'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    short_description = db.Column(db.String(200))
    developer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    cover_image = db.Column(db.String(100), nullable=False)
    download_link = db.Column(db.String(256), nullable=False)
    version = db.Column(db.String(20))
    is_approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    download_count = db.Column(db.Integer, default=0)
    cost = db.Column(db.Float, default=0.0)
    is_free = db.Column(db.Boolean, default=True)
    ratings = db.relationship('Rating', backref='game', lazy=True, cascade='all, delete-orphan')
    
    @property
    def cover_url(self):
        return url_for('static', filename=f'uploads/game_covers/{self.cover_image}')

    @property
    def average_rating(self):
        if not self.ratings:
            return 0
        valid_ratings = [r.score for r in self.ratings if r.is_approved]
        if not valid_ratings:
            return 0
        return sum(valid_ratings) / len(valid_ratings)

class Rating(db.Model):
    __tablename__ = 'ratings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    review = db.Column(db.Text)
    is_approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'game_id', name='_user_game_uc'),
    )

class DeveloperRequest(db.Model):
    __tablename__ = 'developer_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='developer_requests')

    STATUSES = ['pending', 'approved', 'rejected']

    def approve(self):
        if self.status == 'pending':
            self.status = 'approved'
            self.user.promote_to_developer()

    def reject(self):
        if self.status == 'pending':
            self.status = 'rejected'

class Purchase(db.Model):
    __tablename__ = 'purchases'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='purchases')
    game = db.relationship('Game', backref='purchases')
