from functools import wraps
from flask import Flask, request, session, redirect, url_for
from flask import render_template_string, jsonify

from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from furl import furl
import requests
import json
import uuid

DATABASE_URI = 'sqlite:///./dohub.db'
SECRET_KEY = 'dohub'
DEBUG = True

# Set these values
GITHUB_CLIENT_ID = '3ee19bc1b2b6e07b190f'
GITHUB_CLIENT_SECRET = '0b64b39fb19aae0ddc40ea10dd6d16fea7eeb86f'

# setup flask
app = Flask(__name__)
app.config.from_object(__name__)

# setup sqlalchemy
engine = create_engine(app.config['DATABASE_URI'])
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    github_access_token = Column(String(255))
    github_id = Column(Integer)
    username = Column(String(255))
    access_key = Column(String(255))
    server_ip = Column(String(15))
    pod_name = Column(String(255))
    role = Column(String(255))
    last_activity = Column(Float)

    def __init__(self, username):
        self.username = username

class ServerOption(Base):
    __tablename__ = 'server_options'

    id = Column(Integer, primary_key=True)
    profile_name = Column(String(255))
    description = Column(String(1000))
    config = Column(String(255))

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
            setattr(self, property, value)

    def __repr__(self):
        return str(self.id)

class GitAuth():
    BASE_URL = 'https://api.github.com/'
    BASE_AUTH_URL = 'https://github.com/login/oauth/'

    def __init__(self, app=None, db=None):
        if app is not None:
            self.db = db
            self.app = app
            self.init_app(self.app)
        else:
            self.db = None
            self.app = None

    def init_app(self, app):
        self.client_id = app.config['GITHUB_CLIENT_ID']
        self.client_secret = app.config['GITHUB_CLIENT_SECRET']
        self.base_url = app.config.get('GITHUB_BASE_URL', self.BASE_URL)
        self.auth_url = app.config.get('GITHUB_AUTH_URL', self.BASE_AUTH_URL)
        # self.session = requests.session()

    def oauth_login(self):
        params = {
            'client_id': self.client_id,
            'scope': 'read:user',
            'state': 'An unguessable random string.',
            'allow_signup': 'true'
        }
        url = furl(self.auth_url + 'authorize').set(params)
        return redirect(str(url), 302)
    
    def handle_callback(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):

            if not 'code' in request.args:
                return {'message': 'no permission'}, 400

            code = request.args.get('code')

            payload = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'state': 'An unguessable random string.'
            }
            r = requests.post(self.BASE_AUTH_URL + 'access_token', json=payload, headers={'Accept': 'application/json'})
            if not 'code' in json.loads(r.text):
                return {'message': 'no permission'}, 400
            access_token = json.loads(r.text)['access_token']
            
            access_user_url = self.BASE_URL + 'user'
            r = requests.get(access_user_url, headers={'Authorization': 'token ' + access_token})
            user = json.loads(r.text)
            user['access_token'] = access_token
            
            return f(*((user,) + args), **kwargs)
        return decorated
    
    def verify(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = None
            if not 'user_access_key' in session:
                user = None
            else:
                user = User.query.filter_by(access_key=session['user_access_key']).first().__dict__
            return f(*((user,) + args), **kwargs)
        return decorated
        
    def login_user(self, user):
        access_key = uuid.uuid4()
        user.access_key = str(access_key)
        db_session.commit()
        session['user_access_key'] = user.access_key
        return

    def logout_user(self):
        session.pop('user_access_key', None)
        return

auth = GitAuth(app, db_session)

# g.user = User.query.get(session['user_id'])

@app.before_first_request
def initialize_database():
    Base.metadata.create_all(bind=engine)


@app.after_request
def after_request(response):
    db_session.remove()
    return response


@app.route('/')
@auth.verify
def index(user):
    if user:
        t = 'Hello! %s <a href="{{ url_for("user") }}">Get user</a> ' \
            '<a href="{{ url_for("index") }}">Get repo</a> ' \
            '<a href="{{ url_for("logout") }}">Logout</a>'
        t %= user['username']
    else:
        t = 'Hello! <a href="{{ url_for("login") }}">Login</a>'

    return render_template_string(t)


@app.route('/github-callback')
@auth.handle_callback
def authorized(user):
    user_ = User.query.filter_by(username=user['login']).first()
    if user_ is None:
        user_ = User(username=user['login'])
        db_session.add(user_)

    user_.github_access_token = user['access_token']
    user_.github_id = int(user['id'])
    db_session.commit()

    auth.login_user(user_)

    return redirect(url_for('index'))


@app.route('/login')
@auth.verify
def login(user):
    if user is None:
        return auth.oauth_login()
    else:
        return redirect(url_for('index'))


@app.route('/logout')
def logout():
    auth.logout_user()
    return redirect(url_for('index'))


@app.route('/user')
@auth.verify
def user(user):
    if not user:
        return redirect(url_for('index'))
    return user['username'], 200


if __name__ == '__main__':
    app.run("0.0.0.0", 5000, debug=False)