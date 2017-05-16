from hashlib import md5
import re
from app import db
from app import app
from app import whooshee
from flask import flash
import logging
from logging.handlers import RotatingFileHandler


import sys
if sys.version_info >= (3, 0):
    enable_search = False
else:
    enable_search = True

followers = db.Table(
    'followers', db.Model.metadata,
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

postFollowers = db.Table(
    'postFollowers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'))
)

rideSharers = db.Table(
    'rideSharers',
    db.Column('sharer_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'))
)


@whooshee.register_model('nickname')
class User(db.Model):
    __searchable__ = ['nickname']

    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password = db.Column(db.String(120), index=True, unique=True)
    address = db.Column(db.String(64), index=True)
    city = db.Column(db.String(64), index=True)
    state = db.Column(db.String(2), index=True)
    zipcode = db.Column(db.Integer, index = True)
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime)

    followed = db.relationship('User',
                               secondary=followers,
                               primaryjoin=(followers.c.follower_id == id),
                               secondaryjoin=(followers.c.followed_id == id),
                               backref=db.backref('followers', lazy='dynamic'),
                               lazy='dynamic')

    followedPosts = db.relationship('Post',
                               secondary=postFollowers,
                               backref=db.backref('postFollowers', lazy='dynamic'),
                               lazy='dynamic')
    sharingPosts = db.relationship('Post',
                               secondary=rideSharers,
                               backref=db.backref('rideSharers', lazy='dynamic'),
                               lazy='dynamic')


    avatar_url = db.Column(db.String(120))

    @staticmethod
    def make_valid_nickname(nickname):
        return re.sub('[^a-zA-Z0-9_\.]', '', nickname)

    @staticmethod
    def make_unique_nickname(nickname):
        if User.query.filter_by(nickname=nickname).first() is None:
            return nickname
        version = 2
        while True:
            new_nickname = nickname + str(version)
            if User.query.filter_by(nickname=new_nickname).first() is None:
                break
            version += 1
        return new_nickname

    @classmethod
    def is_user_name_taken(cls, user_name):
        return db.session.query(db.exists().where(User.nickname==user_name)).scalar()

    @classmethod
    def is_email_taken(cls, email_address):
        return db.session.query(db.exists().where(User.email==email_address)).scalar()

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        try:
            return unicode(self.id)  # python 2
        except NameError:
            return str(self.id)  # python 3

    def avatar(self, size): # we don't actually use the "size" parameter
        avatar_url = self.avatar_url
        if avatar_url is None:
            return "/static/img/default.png"
        return avatar_url

    #*****************************************************************************
    def requestT(self, post):
        if not self.has_requested(post):
            self.followedPosts.append(post)
            return self

    def has_requested(self, post):
        return self.followedPosts.filter(
            postFollowers.c.post_id == post.id).count() > 0

    def unrequest(self, post):
        if self.has_requested(post):
            self.followedPosts.remove(post)
            return self

    def requested_posts(self):
        return Post.query.join(postFollowers, (postFollowers.c.post_id == Post.id)).filter(postFollowers.c.follower_id == self.id).order_by(Post.timestamp.desc())

    #*****************************************************************************
    def addRideshare(self, post):
        self.sharingPosts.append(post)
        return self

    def shared_posts(self):
        if ((Post.query.filter_by(id=rideSharers.c.post_id).first()) is not None):
            postT = Post.query.join(rideSharers, (rideSharers.c.post_id == Post.id)).filter((Post.query.filter_by(id=rideSharers.c.post_id).first()).author.id == self.id)
            return (postT.union(Post.query.join(rideSharers, (rideSharers.c.post_id == Post.id)).filter(rideSharers.c.sharer_id == self.id))).order_by(Post.timestamp.desc())
        return Post.query.join(rideSharers, (rideSharers.c.post_id == Post.id)).filter(rideSharers.c.sharer_id == self.id).order_by(Post.timestamp.desc())

    #*****************************************************************************

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)
            return self

    def diffShare(self):
        #flash(self.posts.count())
        #flash(self.id)
        #flash(Post.query.join(rideSharers, (rideSharers.c.post_id == Post.id)).filter((Post.query.filter_by(id=rideSharers.c.post_id).first()).author.id == self.id).count())
        if (Post.query.filter_by(id=rideSharers.c.post_id).first()) is None:
            return 1;

        return self.posts.count() - (Post.query.join(rideSharers, (rideSharers.c.post_id == Post.id)).filter((Post.query.filter_by(id=rideSharers.c.post_id).first()).author.id == self.id).count())

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)
            return self

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        return Post.query.join(followers, (followers.c.followed_id == Post.user_id)).filter(followers.c.follower_id == self.id).order_by(Post.timestamp.desc())



    def neighborPosts(self):
        return Post.query.filter(Post.user_zipcode == self.zipcode).order_by(Post.timestamp.desc())

    def __repr__(self):  # pragma: no cover
        return '<User %r>' % (self.nickname)




@whooshee.register_model('body','destination')
class Post(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    destination = db.Column(db.String(120))
    trip_date = db.Column(db.Date)
    trip_time = db.Column(db.Time)
    seats = db.Column(db.Integer)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user_zipcode = db.Column(db.Integer)
    language = db.Column(db.String(5))
    needRide = db.Column(db.Boolean)
    accepted = db.Column(db.Boolean)


    followersP = db.relationship('User',
                               secondary=postFollowers,
                               backref=db.backref('postFollowers', lazy='dynamic'),
                               lazy='dynamic')

    rideSharersP = db.relationship('User',
                               secondary=rideSharers,
                               backref=db.backref('rideSharers', lazy='dynamic'),
                               lazy='dynamic')

    def is_followedBy(self, user):
        return self.followersP.filter(
            postFollowers.c.follower_id == user.id).count() > 0
    def allFollowers(self):
        return User.query.join(postFollowers, (postFollowers.c.follower_id == User.id)).filter(postFollowers.c.post_id == self.id)#.order_by(Post.timestamp.desc())
    def hasFollowers(self):
        return (self.allFollowers().count() > 0)


    def is_sharingWith(self, user):
        return self.rideSharersP.filter(
            rideSharers.c.sharer_id == user.id).count() > 0
    def allSharers(self):
        return User.query.join(rideSharers, (rideSharers.c.sharer_id == User.id)).filter(rideSharers.c.post_id == self.id)#.order_by(Post.timestamp.desc())
    def hasSharers(self):
        return (self.allSharers().count() > 0)

    def acceptRequest(self, user):
        self.accepted = True;
        if not self.is_sharingWith(user):
            self.rideSharersP.append(user)
            #need to change if multiple spots available 
            #user.addRideshare(post)
            for user in self.followersP:
                user.unrequest(self)

            return self


    def __repr__(self):  # pragma: no cover
        return '<Post %r>' % (self.body)


#if enable_search:
#    flask_whooshalchemy.whoosh_index(app, Post)
