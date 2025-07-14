from sqlite3 import IntegrityError
from flask import Blueprint, jsonify, render_template, redirect, send_from_directory, url_for, flash, request, abort, session, current_app
from flask_login import login_user, current_user, logout_user, login_required
from sqlalchemy import func
from sqlalchemy import desc as sql_desc
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from forms import RegistrationForm, LoginForm, ResetPasswordForm, TwoFactorForm, ProfileForm, ChangePasswordForm, GameForm, RatingForm, ForgotPasswordForm
from models import User, Game, Rating, DeveloperRequest, Purchase
from extensions import db, login_manager, bcrypt, mail
from utils import save_picture, allowed_file, send_reset_email
from utils import send_verification_email, generate_verification_code
import os
import pyotp
from datetime import datetime
from itsdangerous import TimedSerializer as Serializer

bp = Blueprint('main', __name__)

@bp.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)

def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(current_app.root_path,
                                     endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)

@bp.route('/admin/user/<int:user_id>/update', methods=['POST'])
@login_required
def update_user(user_id):
    if not current_user.is_admin:
        abort(403)

    user = User.query.get_or_404(user_id)

    user.is_developer = 'is_developer' in request.form
    user.is_moderator = 'is_moderator' in request.form

    
    if current_user.id != user.id:
        user.is_admin = 'is_admin' in request.form


    db.session.commit()
    flash(f"მომხმარებლის როლები განახლდა: {user.username}", "success")
    return redirect(url_for('main.manage_users'))


@bp.route('/game/<int:game_id>/delete', methods=['POST'])
@login_required
def delete_game(game_id):
    game = Game.query.get_or_404(game_id)

    if current_user.id != game.developer_id and not (current_user.is_admin or current_user.is_moderator):
        abort(403)

    try:
        if game.cover_image:
            cover_path = os.path.join(current_app.root_path, 'static', 'uploads', 'game_covers', game.cover_image)
            if os.path.exists(cover_path):
                os.remove(cover_path)

        db.session.delete(game)
        db.session.commit()
        flash('თამაში წარმატებით წაიშალა!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('შეცდომა მოხდა თამაშის წაშლის დროს.', 'danger')

    return redirect(url_for('main.list_games'))



@bp.route('/admin/user/<int:user_id>/delete')
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        abort(403)

    user = User.query.get_or_404(user_id)

    if current_user.id == user.id:
        flash("თქვენ არ შეგიძლიათ საკუთარი თავის წაშლა!", "danger")
        return redirect(url_for('main.manage_users'))

    db.session.delete(user)
    try:
        db.session.commit()
        flash(f"მომხმარებელი {user.username} წარმატებით წაიშალა", "success")
    except:
        db.session.rollback()
        flash("წაშლისას მოხდა შეცდომა", "danger")

    return redirect(url_for('main.manage_users'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(
                username=form.username.data,
                email=form.email.data
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()

            code = generate_verification_code()
            user.verification_code = code
            db.session.commit()

            send_verification_email(user, code)
            session['user_id'] = user.id
            flash('თქვენი ანგარიში შეიქმნა! გთხოვთ შეიყვანოთ კოდი დასადასტურებლად.', 'success')
            return redirect(url_for('main.two_factor'))
        
        except IntegrityError as e:
            db.session.rollback()
            if "username" in str(e):
                flash('ეს სახელი უკვე გამოყენებულია', 'danger')
            elif "email" in str(e):
                flash('ეს ელ.ფოსტა უკვე რეგისტრირებულია', 'danger')
            else:
                flash('დაფიქსირდა შეცდომა რეგისტრაციის დროს', 'danger')

    return render_template('auth/register.html', title='რეგისტრაცია', form=form)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and user.check_password(form.password.data):
            code = generate_verification_code()
            user.verification_code = code
            db.session.commit()

            send_verification_email(user, code)
            session['user_id'] = user.id
            session['remember'] = form.remember.data

            flash('გთხოვთ შეიყვანოთ დადასტურების კოდი.', 'info')
            return redirect(url_for('main.two_factor'))
        else:
            flash('შესვლა ვერ მოხერხდა. გთხოვთ შეამოწმოთ ელ.ფოსტა და პაროლი', 'danger')

    return render_template('auth/login.html', title='შესვლა', form=form)


@bp.route('/two-factor', methods=['GET', 'POST'])
def two_factor():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('main.login'))

    form = TwoFactorForm()
    if form.validate_on_submit():
        if form.token.data == user.verification_code:
            login_user(user, remember=session.get('remember', False))
            user.last_login = datetime.utcnow()
            user.verification_code = None
            db.session.commit()

            session.pop('user_id', None)
            session.pop('remember', None)

            flash('თქვენ შეხვედით სისტემაში!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('არასწორი კოდი. სცადეთ თავიდან.', 'danger')

    return render_template('auth/two_factor.html', title='ორფაქტორიანი ავთენტიფიკაცია', form=form)

@bp.route('/resend-2fa')
def resend_2fa():
    user_id = session.get('user_id')
    if not user_id:
        flash('მომხმარებელი ვერ მოიძებნა.', 'danger')
        return redirect(url_for('main.login'))

    user = User.query.get(user_id)
    if user:
        code = generate_verification_code()
        user.verification_code = code
        db.session.commit()
        send_verification_email(user, code)
        flash('კოდი ხელახლა გაგზავნილია.', 'success')
    else:
        flash('მომხმარებელი ვერ მოიძებნა.', 'danger')

    return redirect(url_for('main.two_factor'))

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('თქვენ გამოხვედით სისტემიდან.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/verify-email/<token>')
def verify_email(token):
    if current_user.is_authenticated:
        logout_user()
    
    user = User.verify_reset_token(token)
    if not user:
        flash('არასწორი ან ვადაგასული ტოკენი', 'warning')
        return redirect(url_for('main.login'))
    
    if user.is_verified:
        flash('ანგარიში უკვე დადასტურებულია. გთხოვთ შეხვიდეთ.', 'info')
    else:
        user.is_verified = True
        db.session.commit()
        flash('თქვენი ელ.ფოსტა დადასტურდა! ახლა შეგიძლიათ შეხვიდეთ.', 'success')
    
    return redirect(url_for('main.login'))

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_reset_email(user)
            flash('ელ.ფოსტაზე გამოგიგზავნეთ პაროლის აღდგენის ინსტრუქციები.', 'info')
            return redirect(url_for('main.login'))
        else:
            flash('ამ ელ.ფოსტით რეგისტრირებული ანგარიში არ მოიძებნა.', 'warning')
    
    return render_template('auth/forgot_password.html', title='პაროლის აღდგენა', form=form)

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    user = User.verify_reset_token(token)
    if not user:
        flash('არასწორი ან ვადაგასული ტოკენი', 'warning')
        return redirect(url_for('main.forgot_password'))
    
    from forms import ResetPasswordForm
    form = ResetPasswordForm()

    if form.validate_on_submit():
        user.set_password(form.new_password.data)
        db.session.commit()
        flash('თქვენი პაროლი წარმატებით შეიცვალა! ახლა შეგიძლიათ შეხვიდეთ.', 'success')
        return redirect(url_for('main.login'))
    
    return render_template('auth/reset_password.html', title='პაროლის აღდგენა', form=form)


@bp.route('/')
def index():
    featured_games = Game.query\
                        .filter_by(is_approved=True)\
                        .order_by(db.func.random())\
                        .limit(4)\
                        .all()
    
    latest_games = Game.query\
                      .filter_by(is_approved=True)\
                      .order_by(sql_desc(Game.created_at))\
                      .limit(4)\
                      .all()

    top_rated = db.session.query(Game)\
                          .join(Rating)\
                          .filter(Game.is_approved == True, Rating.is_approved == True)\
                          .group_by(Game.id)\
                          .order_by(sql_desc(func.avg(Rating.score)))\
                          .limit(4)\
                          .all()

    return render_template('index.html', title='მთავარი',
                           featured_games=featured_games,
                           latest_games=latest_games,
                           top_rated=top_rated)

@bp.route('/help')
def help():
    return render_template('help.html', title='დახმარება')

@bp.route('/games')
def list_games():
    page = request.args.get('page', 1, type=int)
    games = Game.query.filter_by(is_approved=True)\
                     .order_by(Game.created_at.desc())\
                     .paginate(page=page, per_page=10)
    return render_template('games/list.html', title='თამაშები', games=games)

@bp.route('/game/<int:game_id>')
def game_detail(game_id):
    game = Game.query.get_or_404(game_id)
    if not game.is_approved and not (current_user.is_authenticated and 
                                   (current_user.is_admin or current_user.is_moderator or current_user.id == game.developer_id)):
        abort(403)
    
    form = None
    user_rating = None
    if current_user.is_authenticated:
        form = RatingForm()
        user_rating = Rating.query.filter_by(user_id=current_user.id, game_id=game.id).first()
    
    return render_template('games/detail.html', 
                         title=game.title,
                         game=game,
                         form=form,
                         user_rating=user_rating)

@bp.route('/game/add', methods=['GET', 'POST'])
@login_required
def add_game():
    if not current_user.is_developer:
        abort(403)
    
    form = GameForm()

    if form.validate_on_submit():
        if not allowed_file(form.cover_image.data.filename):
            flash('არასწორი ფაილის ტიპი სახეხსახურისთვის', 'danger')
            return render_template('games/add.html', title='თამაშის დამატება', form=form)

        cover_filename = save_picture(form.cover_image.data, 'game_covers')
        
        is_free = form.is_free.data
        cost = 0.0 if is_free else float(form.cost.data or 0)
        
        game = Game(
            title=form.title.data,
            short_description=form.short_description.data,
            description=form.description.data,
            developer_id=current_user.id,
            cover_image=cover_filename,
            download_link=form.download_link.data,
            version=form.version.data,
            is_approved=current_user.is_admin or current_user.is_moderator,
            is_free=is_free,
            cost=cost
        )
        
        db.session.add(game)
        db.session.commit()
        
        flash('თქვენი თამაში წარმატებით დაემატა მიმოხილვისთვის!' if not game.is_approved else 'თქვენი თამაში წარმატებით გამოქვეყნდა!', 'success')
        return redirect(url_for('main.game_detail', game_id=game.id))
    
    return render_template('games/add.html', title='თამაშის დამატება', form=form)


@bp.route('/game/<int:game_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_game(game_id):
    game = Game.query.get_or_404(game_id)
    
    if current_user.id != game.developer_id and not (current_user.is_admin or current_user.is_moderator):
        abort(403)
    
    form = GameForm(obj=game)
    if form.validate_on_submit():
        if form.cover_image.data:
            if not allowed_file(form.cover_image.data.filename):
                flash('არასწორი ფაილის ტიპი პროფილის ფოტოსთვის', 'danger')
                return redirect(url_for('main.edit_game', game_id=game.id))

            old_cover = os.path.join(current_app.root_path, 'static', 'uploads', 'game_covers', game.cover_image)
            if os.path.exists(old_cover):
                os.remove(old_cover)
            
            game.cover_image = save_picture(form.cover_image.data, 'game_covers')
        
        game.title = form.title.data
        game.short_description = form.short_description.data
        game.description = form.description.data
        game.download_link = form.download_link.data
        game.version = form.version.data
        game.is_free = form.is_free.data
        game.cost = 0.0 if form.is_free.data else float(form.cost.data or 0)
        
        if current_user.is_admin or current_user.is_moderator:
            game.is_approved = True
        
        db.session.commit()
        flash('თქვენი თამაში წარმატებით განახლდა!', 'success')
        return redirect(url_for('main.game_detail', game_id=game.id))
    
    elif request.method == 'GET':
        form.is_free.data = game.is_free
        form.cost.data = int(game.cost or 0)
    
    return render_template('games/edit.html', title='თამაშის რედაქტირება', form=form, game=game)

@bp.route('/game/<int:game_id>/rate', methods=['POST'])
@login_required
def rate_game(game_id):
    game = Game.query.get_or_404(game_id)
    form = RatingForm()
    
    if form.validate_on_submit():
        rating = Rating.query.filter_by(user_id=current_user.id, game_id=game.id).first()
        
        if rating:
            rating.score = form.score.data
            rating.review = form.review.data
        else:
            rating = Rating(
                user_id=current_user.id,
                game_id=game.id,
                score=form.score.data,
                review=form.review.data
            )
            db.session.add(rating)
        
        db.session.commit()
        flash('თქვენი შეფასება წარმატებით დაემატა!', 'success')
    
    return redirect(url_for('main.game_detail', game_id=game.id))

@bp.route('/game/<int:game_id>/download')
def download_game(game_id):
    game = Game.query.get_or_404(game_id)
    if not game.is_approved and not (current_user.is_authenticated and 
                                   (current_user.is_Owner or current_user.is_admin or current_user.is_moderator or current_user.id == game.developer_id)):
        abort(403)
    
    game.download_count += 1
    db.session.commit()
    
    return redirect(game.download_link)

@bp.route('/profile/view')
@login_required
def view_profile():
    developer_stats = None
    if current_user.is_developer:
        games = Game.query.filter_by(developer_id=current_user.id).all()
        game_count = len(games)
        total_downloads = sum(game.download_count for game in games)
        total_ratings = sum(len(game.ratings) for game in games)
        average_rating = None

        if total_ratings > 0:
            total_score = sum(rating.score for game in games for rating in game.ratings)
            average_rating = total_score / total_ratings

        developer_stats = {
            'game_count': game_count,
            'total_downloads': total_downloads,
            'average_rating': average_rating
        }

    return render_template('profile/view.html',
                           title='პროფილი',
                           developer_stats=developer_stats)

@bp.route('/admin/developer-request/<int:request_id>/<action>', methods=['GET', 'POST'])
@login_required
def handle_developer_request(request_id, action):
    if not current_user.is_admin:
        abort(403)

    dev_request = DeveloperRequest.query.get_or_404(request_id)

    if action == 'approve':
        user = dev_request.user
        user.is_developer = True
        db.session.delete(dev_request)
        db.session.commit()
        flash(f"{user.username} დამტკიცდა როგორც დეველოპერი", 'success')
    elif action == 'reject':
        db.session.delete(dev_request)
        db.session.commit()
        flash("მოთხოვნა უარყოფილია", 'warning')
    else:
        abort(400)

    return redirect(url_for('main.developer_requests'))


@bp.route('/admin/developer-requests')
@login_required
def developer_requests():
    if not current_user.is_admin:
        abort(403)

    requests = DeveloperRequest.query.order_by(DeveloperRequest.created_at.desc()).all()
    return render_template('admin/developer_requests.html', requests=requests)


@bp.route('/ratings/<int:rating_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_rating(rating_id):
    rating = Rating.query.get_or_404(rating_id)

    if current_user.id != rating.user_id:
        abort(403)

    form = RatingForm(obj=rating)

    if form.validate_on_submit():
        rating.score = form.score.data
        rating.review = form.review.data
        db.session.commit()
        flash('შეფასება წარმატებით შეიცვალა.', 'success')
        return redirect(url_for('main.game_detail', game_id=rating.game_id))

    return render_template('games/edit_rating.html', form=form, rating=rating)


@bp.route('/ratings/<int:rating_id>/delete', methods=['POST'])
@login_required
def delete_rating(rating_id):
    rating = Rating.query.get_or_404(rating_id)

    if current_user.id != rating.user_id and not (current_user.is_admin or current_user.is_moderator):
        abort(403)

    db.session.delete(rating)
    db.session.commit()
    flash('შეფასება წაიშალა.', 'success')
    return redirect(url_for('main.game_detail', game_id=rating.game_id))


@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    
    form = ProfileForm()
    
    if form.validate_on_submit():
        if form.avatar.data:
            if current_user.avatar:
                old_avatar = os.path.join(current_app.root_path, 'static', 'uploads', 'avatars', current_user.avatar)
                if os.path.exists(old_avatar):
                    os.remove(old_avatar)
            
            avatar_filename = save_picture(form.avatar.data, 'avatars')
            current_user.avatar = avatar_filename
        
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        
        flash('თქვენი პროფილი წარმატებით განახლდა!', 'success')
        return redirect(url_for('main.view_profile'))
    
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    
    return render_template('profile/edit.html', title='პროფილის რედაქტირება', form=form)

@bp.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        current_user.set_password(form.new_password.data)
        db.session.commit()
        
        flash('თქვენი პაროლი წარმატებით შეიცვალა!', 'success')
        return redirect(url_for('main.view_profile'))
    
    return render_template('profile/change_password.html', title='პაროლის შეცვლა', form=form)

@bp.route('/developer/request', methods=['GET', 'POST'])
@login_required
def request_developer():

    if current_user.is_developer:
        flash('თქვენ უკვე დეველოპერი ხართ.', 'info')
        return redirect(url_for('main.view_profile'))

    if request.method == 'POST':

        existing_request = DeveloperRequest.query.filter_by(user_id=current_user.id).first()
        if existing_request:
            flash('თქვენ უკვე გაგზავნილია დეველოპერის სტატუსის მოთხოვნა.', 'info')
        else:
            new_request = DeveloperRequest(user_id=current_user.id, status='pending')
            db.session.add(new_request)
            db.session.commit()
            flash('თქვენი დეველოპერის სტატუსის მოთხოვნა გაგზავნილია.', 'success')
        return redirect(url_for('main.view_profile'))

    return render_template('developer/request_developer.html', title='დეველოპერის სტატუსის მოთხოვნა')


@bp.route('/developer/dashboard')
@login_required
def developer_dashboard():
    if not current_user.is_developer:
        abort(403)
    
    games = Game.query.filter_by(developer_id=current_user.id)\
                     .order_by(Game.created_at.desc())\
                     .all()
    
    total_downloads = sum(game.download_count for game in games)
    total_ratings = sum(len(game.ratings) for game in games)
    average_rating = None
    
    if total_ratings > 0:
        total_score = sum(rating.score for game in games for rating in game.ratings)
        average_rating = total_score / total_ratings
    
    return render_template('profile/developer_dashboard.html',
                         title='დეველოპერის პანელი',
                         games=games,
                         total_downloads=total_downloads,
                         average_rating=average_rating)

@bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin and not current_user.is_moderator:
        abort(403)
    
    pending_games = Game.query.filter_by(is_approved=False).count()
    total_users = User.query.count()
    total_games = Game.query.count()
    
    return render_template('admin/dashboard.html',
                         title='ადმინის პანელი',
                         pending_games=pending_games,
                         total_users=total_users,
                         total_games=total_games)

@bp.route('/admin/users')
@login_required
def manage_users():
    if not current_user.is_admin:
        abort(403)
    
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.created_at.desc())\
                     .paginate(page=page, per_page=20)
    
    return render_template('admin/users.html',
                         title='მომხმარებლების მართვა',
                         users=users)

@bp.route('/admin/user/<int:user_id>/toggle-role/<role>')
@login_required
def toggle_user_role(user_id, role):
    if not current_user.is_admin:
        abort(403)
    
    user = User.query.get_or_404(user_id)
    
    if role == 'developer':
        user.is_developer = not user.is_developer
    elif role == 'moderator':
        user.is_moderator = not user.is_moderator
    elif role == 'admin' and current_user.id != user_id:
        user.is_admin = not user.is_admin
    
    db.session.commit()
    flash(f'მომხმარებელი {user.username}-ის როლი განახლდა', 'success')
    return redirect(url_for('main.manage_users'))

@bp.route('/admin/games')
@login_required
def manage_games():
    if not current_user.is_admin and not current_user.is_moderator:
        abort(403)
    
    page = request.args.get('page', 1, type=int)
    
    games = Game.query.order_by(Game.created_at.desc())\
                      .paginate(page=page, per_page=20)
    
    return render_template('admin/games.html',
                           title='თამაშების მართვა',
                           games=games)

@bp.app_errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html', error=error), 403

@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@bp.route('/robots.txt')
def robots():
    return send_from_directory(current_app.static_folder, 'robots.txt')

@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500


@bp.route('/avatars/<filename>')
def get_avatar(filename):
    avatar_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'avatars')
    return send_from_directory(avatar_folder, filename)


