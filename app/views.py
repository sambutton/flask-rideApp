import sys, json, os, boto3
from flask import Flask, render_template, flash, redirect, session, url_for, request, \
    g, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from flask_sqlalchemy import get_debug_queries
from flask_babel import gettext
from datetime import datetime
from app import app, db, lm, babel, whooshee
from .forms import LoginForm, EditForm, PostForm, SearchForm, SignUpForm
from .models import User, Post
from .emails import request_notification
from .translate import microsoft_translate
from config import POSTS_PER_PAGE, MAX_SEARCH_RESULTS, LANGUAGES, \
    DATABASE_QUERY_TIMEOUT, AWS_SECRET_KEY, AWS_ACCESS_KEY


@lm.user_loader
def load_user(id):
    return User.query.get(int(id))

@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(LANGUAGES.keys())


@app.before_request
def before_request():
    g.user = current_user
    if g.user.is_authenticated:
        g.user.last_seen = datetime.utcnow()
        db.session.add(g.user)
        db.session.commit()
        g.search_form = SearchForm()
    g.locale = get_locale()


@app.after_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= DATABASE_QUERY_TIMEOUT:
            app.logger.warning(
                "SLOW QUERY: %s\nParameters: %s\nDuration: %fs\nContext: %s\n" %
                (query.statement, query.parameters, query.duration,
                 query.context))
    return response


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@app.route('/index/<int:page>', methods=['GET', 'POST'])
@login_required
def index(page=1):
    posts = g.user.neighborPosts().paginate(page, POSTS_PER_PAGE, False)
    return render_template('index.html',
                           title='Home',
                           posts=posts)


@app.route('/makeTrip', methods=['GET', 'POST'])
def makeTrip(page=1):
    form = PostForm()
    if form.validate_on_submit():
        language = 'en'
        if language == 'UNKNOWN' or len(language) > 5:
            language = ''
        if form.needRide.data == 'Need a ride':
            needRide = True;
        else:
            needRide = False;
        post = Post(destination=form.destination.data, seats=form.seats.data, needRide=needRide, trip_date=form.trip_date.data, trip_time=form.trip_time.data, body=form.body.data, timestamp=datetime.utcnow(),
                    author=g.user, language=language, user_zipcode=g.user.zipcode, accepted=False)
        db.session.add(post)
        db.session.commit()
        flash(gettext('Your post is now live!'))
        return redirect(url_for('index'))
    return render_template('makeTrip.html',
                           title='make',
                           form=form)

#@oid.loginhandler
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    try:
        if g.user is not None and g.user.is_authenticated:
            return redirect(url_for('index'))
        if form.validate_on_submit():
            session['remember_me'] = form.remember_me.data
            user = User.query.filter_by(email=form.email.data).first()
            if user:
                if user.password == form.password.data:
                    user.authenticated = True
                    db.session.add(user)
                    db.session.commit()
                    succ = login_user(user)
                    #flash('Logged in %s.' % (user.nickname,))
                    next = request.args.get('next')
                    return redirect(next or url_for('index'))
            flash("Invalid username or password")
        return render_template('login.html',
                               title='Sign In',
                               form=form)
    except Exception as e:
        flash('Login failed.')
        return render_template('login.html',
                               title='Sign In',
                               form=form)

#@oid.after_login
#def after_login(resp):
#    if resp.email is None or resp.email == "":
#        flash(gettext('Invalid login. Please try again.'))
#        return redirect(url_for('login'))
#    user = User.query.filter_by(email=resp.email).first()
#    if user is None:
#        nickname = resp.nickname
#        if nickname is None or nickname == "":
#            nickname = resp.email.split('@')[0]
#        nickname = User.make_valid_nickname(nickname)
#        nickname = User.make_unique_nickname(nickname)
#        user = User(nickname=nickname, email=resp.email)
#        db.session.add(user)
#        db.session.commit()
#        # make the user follow him/herself
#        db.session.add(user.follow(user))
#        db.session.commit()
#    remember_me = False
#    if 'remember_me' in session:
#        remember_me = session['remember_me']
#        session.pop('remember_me', None)
#    login_user(user, remember=remember_me)
#    return redirect(request.args.get('next') or url_for('index'))

@app.route('/signUp',methods=['POST','GET'])
def signUp():
    form = SignUpForm()
    try:
        if g.user is not None and g.user.is_authenticated:
            return redirect(url_for('index'))
        if form.validate_on_submit():
            if User.is_user_name_taken(form.name.data):
                flash("This nickname is already taken!")
                return render_template('signUp.html',
                               title='Sign Up',
                               form=form)
            if User.is_email_taken(form.email.data):
                flash("This email is already taken!")
                return render_template('signUp.html',
                               title='Sign Up',
                               form=form)
            session['remember_me'] = form.remember_me.data
            user = User(nickname=form.name.data,email=form.email.data,password=form.password.data, address=form.address.data, city=form.city.data, state=form.state.data, zipcode=form.zipcode.data) 
            user.authenticated = True
            db.session.add(user)
            db.session.commit()
            succ = login_user(user)
            if succ:
                db.session.add(user.follow(user))
                db.session.commit()
                flash('Thank you for registering!')
                next = request.args.get('next')
                #if not is_safe_url(next):
                #    return flask.abort(400)
                return redirect(next or url_for('index'))
            flash('New user was not created successfully')
        return render_template('signup.html',
                               title='Sign Up',
                               form=form)
    except Exception as e:
        flash('Signup failed.')
        return render_template('signUp.html',
                               title='Sign Up',
                               form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/user/<nickname>')
@app.route('/user/<nickname>/<int:page>')
@login_required
def user(nickname, page=1):
    user = User.query.filter_by(nickname=nickname).first()
    if user is None:
        flash(gettext('User %(nickname)s not found.', nickname=nickname))
        return redirect(url_for('index'))
    posts = ((user.posts).order_by(Post.timestamp.desc())).paginate(page, POSTS_PER_PAGE, False)
    posts2 = user.requested_posts().paginate(page, POSTS_PER_PAGE, False)
    posts3 = user.shared_posts().paginate(page, POSTS_PER_PAGE, False)
    return render_template('user.html',
                           user=user,
                           posts=posts,
                           posts2 = posts2, posts3 = posts3)


@app.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    form = EditForm(g.user.nickname)
    if form.validate_on_submit():
        g.user.nickname = form.nickname.data
        g.user.about_me = form.about_me.data
        if form.avatar_url.data !="":
            g.user.avatar_url = form.avatar_url.data
        if form.email.data !="":
            g.user.email = form.email.data
        if form.address.data !="":
            g.user.address = form.address.data
        if form.city.data !="":
            g.user.city = form.city.data
        if form.state.data !="":
            g.user.state = form.state.data
        if form.zipcode.data !="":
            g.user.zipcode = form.zipcode.data
        db.session.add(g.user)
        db.session.commit()
        flash(gettext('Your changes have been saved.'))
        return redirect(url_for('user', nickname=g.user.nickname))
    elif request.method != "POST":
        form.nickname.data = g.user.nickname
        form.about_me.data = g.user.about_me
    return render_template('edit.html', form=form, user =g.user)



@app.route('/sign_s3/')
def sign_s3():
    S3_BUCKET = 'outandaboutuserimages'

    app.logger.info(request.args)
    file_name = request.args.get('file_name')
    file_type = request.args.get('file_type')

    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
    )

    presigned_post = s3.generate_presigned_post(
        Bucket = S3_BUCKET,
        Key = file_name,
        Fields = {"acl": "public-read", "Content-Type": file_type},
        Conditions = [
            {"acl": "public-read"},
            {"Content-Type": file_type}
        ],
        ExpiresIn = 3600
    )

    return json.dumps({
        'data': presigned_post,
        'url': 'https://%s.s3.amazonaws.com/%s' % (S3_BUCKET, file_name)
    })


@app.route('/requestTrip/<post_id>')
@login_required
def requestTrip(post_id):
    post = Post.query.filter_by(id=post_id).first()
    if post is None:
        flash('Post not found.')
        return redirect(url_for('index'))
    if post.author == g.user:
        flash(gettext('You can\'t rideshare with yourself!'))
        return redirect(url_for('user', nickname=g.user.nickname))
    u = g.user.requestT(post)
    if u is None:
        flash(gettext('Cannot connect.'))
        return redirect(url_for('user', nickname=post.author.nickname))
    db.session.add(u)
    db.session.commit()
    flash(gettext('%(nickname)s has been notified that you want to rideshare!', nickname=post.author.nickname))
    request_notification(post.author, g.user)
    return redirect(url_for('index'))

@app.route('/unRequestTrip/<post_id>')
@login_required
def unRequestTrip(post_id):
    post = Post.query.filter_by(id=post_id).first()
    if post is None:
        flash('Post not found.')
        return redirect(url_for('index'))
    if post.author == g.user:
        flash(gettext('You can\'t rideshare with yourself!'))
        return redirect(url_for('user', nickname=g.user.nickname))
    u = g.user.unrequest(post)
    if u is None:
        flash(gettext('Cannot connect.'))
        return redirect(url_for('user', nickname=post.author.nickname))
    db.session.add(u)
    db.session.commit()
    flash(gettext('You have canceled your rideshare with %(nickname)s.',
                  nickname=post.author.nickname))
    return redirect(url_for('index'))

@app.route('/reject/<post_id>/<idU>')
@login_required
def reject(post_id,idU):
    post = Post.query.filter_by(id=post_id).first()
    use = User.query.filter_by(id=idU).first()
    if post is None:
        flash('Post not found.')
        return redirect(url_for('index'))
    if post.author == use:
        flash(gettext('You can\'t rideshare with yourself!'))
        return redirect(url_for('user', nickname=g.user.nickname))
    u = use.unrequest(post)
    if u is None:
        flash(gettext('Cannot connect.'))
        return redirect(url_for('user', nickname=post.author.nickname))
    db.session.add(u)
    db.session.commit()
    flash(gettext('You have rejected your rideshare with %(nickname)s.',
                  nickname=use.nickname))
    return redirect(url_for('index'))

@app.route('/accept/<post_id>/<idU>')
@login_required
def accept(post_id,idU):
    post = Post.query.filter_by(id=post_id).first()
    use = User.query.filter_by(id=idU).first()
    if post is None:
        flash('Post not found.')
        return redirect(url_for('index'))
    if post.author == use:
        flash(gettext('You can\'t rideshare with yourself!'))
        return redirect(url_for('user', nickname=g.user.nickname))
    u = post.acceptRequest(use)
    if u is None:
        flash(gettext('Cannot connect.'))
        return redirect(url_for('user', nickname=post.author.nickname))
    db.session.add(u)
    db.session.commit()
    flash(gettext('You have accepted a rideshare. A connection email has been sent to %(nickname)s.',
                  nickname=use.nickname))
    return redirect(url_for('index'))



@app.route('/follow/<nickname>')
@login_required
def follow(nickname):
    user = User.query.filter_by(nickname=nickname).first()
    if user is None:
        flash('User %s not found.' % nickname)
        return redirect(url_for('index'))
    if user == g.user:
        flash(gettext('You can\'t follow yourself!'))
        return redirect(url_for('user', nickname=nickname))
    u = g.user.follow(user)
    if u is None:
        flash(gettext('Cannot follow %(nickname)s.', nickname=nickname))
        return redirect(url_for('user', nickname=nickname))
    db.session.add(u)
    db.session.commit()
    flash(gettext('You are now following %(nickname)s!', nickname=nickname))
    follower_notification(user, g.user)
    return redirect(url_for('user', nickname=nickname))


@app.route('/unfollow/<nickname>')
@login_required
def unfollow(nickname):
    user = User.query.filter_by(nickname=nickname).first()
    if user is None:
        flash('User %s not found.' % nickname)
        return redirect(url_for('index'))
    if user == g.user:
        flash(gettext('You can\'t unfollow yourself!'))
        return redirect(url_for('user', nickname=nickname))
    u = g.user.unfollow(user)
    if u is None:
        flash(gettext('Cannot unfollow %(nickname)s.', nickname=nickname))
        return redirect(url_for('user', nickname=nickname))
    db.session.add(u)
    db.session.commit()
    flash(gettext('You have stopped following %(nickname)s.',
                  nickname=nickname))
    return redirect(url_for('user', nickname=nickname))


@app.route('/delete/<int:id>')
@login_required
def delete(id):
    post = Post.query.get(id)
    if post is None:
        flash('Post not found.')
        return redirect(url_for('index'))
    if post.author.id != g.user.id:
        flash('You cannot delete this post.')
        return redirect(url_for('index'))
    for user in post.allFollowers():
        u = user.unrequest(post)
        db.session.add(u)
        db.session.commit()
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted.')
    return redirect(url_for('index'))


@app.route('/search', methods=['POST'])
@login_required
def search():
    if not g.search_form.validate_on_submit():
        return redirect(url_for('index'))
    return redirect(url_for('search_results', query=g.search_form.search.data))


@app.route('/search_results/<query>')
@login_required
def search_results(query):
    postResults = Post.query.whooshee_search(query).all()  #  , MAX_SEARCH_RESULTS
    userResults = User.query.whooshee_search(query).all()
    return render_template('search_results.html',
                           query=query,
                           postResults=postResults, userResults=userResults)


@app.route('/translate', methods=['POST'])
@login_required
def translate():
    return jsonify({
        'text': microsoft_translate(
            request.form['text'],
            request.form['sourceLang'],
            request.form['destLang'])})