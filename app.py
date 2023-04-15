from functools import wraps
from flask import Flask, request, session, redirect, url_for, render_template, Response, jsonify

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from furl import furl
import requests
import json
import uuid

import re
from urllib.parse import urlparse, urlunparse
import threading
from flask_sock import Sock
from websocket import create_connection

import yaml

with open("config.yaml", 'r') as stream:
    config_file = yaml.safe_load(stream)

DATABASE_URI = 'sqlite:///./dohub.db'
SECRET_KEY = 'dohub'
DEBUG = True

# Set these values
GITHUB_CLIENT_ID = config_file['githubOauth']['GITHUB_CLIENT_ID']
GITHUB_CLIENT_SECRET = config_file['githubOauth']['GITHUB_CLIENT_SECRET']

# setup flask
app = Flask(__name__)
app.config.from_object(__name__)
sock = Sock(app)

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
    image = Column(Text)
    access_key = Column(String(255))
    server_ip = Column(String(15))
    role = Column(String(255), default='normal_user')
    is_accept = Column(Boolean, unique=False, default=False)
    current_server = Column(Integer, default=1)
    state = Column(String(255), default='offline')
    access_password = Column(String(255))
    last_activity = Column(Float)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
            setattr(self, property, value)

class ServerOption(Base):
    __tablename__ = 'server_options'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True)
    image = Column(String(255), default='logo.png')
    docker_image = Column(String(255), default="daovietanh99/deepops")
    cpu = Column(Integer)
    ram = Column(String(255))
    drive = Column(String(255))
    gpu = Column(String(255))
    color = Column(String(255), default="#fcb040")

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
            setattr(self, property, value)

    def __repr__(self):
        return str(self.id)

class ServerPort(Base):
    __tablename__ = 'server_ports'

    id = Column(Integer, primary_key=True)
    server_id = Column(Integer)
    internal_port = Column(Integer)
    external_port = Column(Integer)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
            setattr(self, property, value)

    def __repr__(self):
        return str(self.id)
    
class UserServer(Base):
    __tablename__ = 'user_server_relations'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    server_id = Column(Integer)

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
                return {'message': 'no permission'}, 403

            code = request.args.get('code')

            payload = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'state': 'An unguessable random string.'
            }
            r = requests.post(self.BASE_AUTH_URL + 'access_token', json=payload, headers={'Accept': 'application/json'})
            if not 'access_token' in json.loads(r.text):
                return {'message': 'no permission'}, 403
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
                user = User.query.filter_by(access_key=session['user_access_key']).first()
                if user:
                    user = user.__dict__
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

@app.before_first_request
def initialize_database():
    Base.metadata.create_all(bind=engine)
    migrate()


@app.after_request
def after_request(response):
    db_session.remove()
    return response


@app.route('/github-callback')
@auth.handle_callback
def authorized(user):
    user_ = User.query.filter_by(username=user['login']).first()
    if user_ is None:
        user_ = User(
            username=user['login'], 
            image=user['avatar_url'], 
            role=("admin" if user['login'] in config_file['admin'] else 'normal_user'), 
            is_accept=user['login'] in config_file['admin'],
            access_password = user['login'] + '-' + str(uuid.uuid4()).split('-')[0]
        )
        db_session.add(user_)
        db_session.commit()

        if user['login'] in config_file['admin']:
            server_ids = db_session.query(ServerOption.id).all()
            for server_id in server_ids:
                userserver = UserServer(user_id=user_.id, server_id=server_id[0])
                db_session.add(userserver)
                db_session.commit()
        else:
            userserver = UserServer(user_id=user_.id, server_id=1)
            db_session.add(userserver)
            db_session.commit()

    user_.github_access_token = user['access_token']
    user_.github_id = int(user['id'])

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

@app.route('/')
@auth.verify
def index(user):
    if user and user['state'] == 'running':
        return redirect("/user/" + user["username"] + "/")
    else:
        return redirect(url_for('hub'))

@app.route('/hub')
@auth.verify
def hub(user):
    if user:
        return render_template('index.html', user=user)
    else:
        return render_template('index.html', user=user)

@app.route('/user_state')
@auth.verify
def user_state(user):
    if not user:
        return jsonify({"message": "no permission"}), 403
    del user['_sa_instance_state']
    all_servers = db_session.query(ServerOption.name) \
            .filter(ServerOption.id == UserServer.server_id) \
            .filter(UserServer.user_id == user['id']) \
            .all()
    current_server = db_session.query(ServerOption.name).filter(ServerOption.id == user['current_server']).first()
    all_servers = [db[0] for db in all_servers]
    user['server_list'] = all_servers
    user['current_server'] = current_server[0]
    return jsonify({'result': user}), 200

@app.route('/all_users')
@auth.verify
def all_user(user):
    if not user:
        return jsonify({"message": "no permission"}), 403
    if not user['role'] == "admin":
        return jsonify({"message": "no permission"}), 403
    users = db_session.query(
        User.id,
        User.username, 
        User.image,
        User.server_ip, 
        User.last_activity, 
        User.role, 
        User.is_accept, 
        ServerOption.name,
        User.state,
        User.access_password) \
        .filter(User.current_server == ServerOption.id).all()
    fields = ['id', 'username', 'image', 'server_ip', 'last_activity', 'role', 'is_accept', 'current_server', 'state', 'access_password', 'server_list']
    result_list = []
    for user in users:
        user_dict = {}
        all_servers = db_session.query(ServerOption.name) \
            .filter(ServerOption.id == UserServer.server_id) \
            .filter(UserServer.user_id == user[0]) \
            .all()
        all_servers = [db[0] for db in all_servers]
        user = list(user)
        user.append(all_servers)
        for i, field in enumerate(fields):
            user_dict[field] = user[i]
        result_list.append(user_dict)
    
    return jsonify({'result': result_list}), 200

@app.route('/all_servers')
def all_server():
    servers = db_session.query(
        ServerOption.name,
        ServerOption.image,
        ServerOption.docker_image,
        ServerOption.cpu,
        ServerOption.ram,
        ServerOption.drive,
        ServerOption.gpu,
        ServerOption.color).all()
    fields = ['name', 'image', 'docker_image', 'cpu', 'ram', 'drive', 'gpu', 'color']
    result_list = {}
    for server in servers:
        server_dict = {}
        for i, field in enumerate(fields):
            server_dict[field] = server[i] if server[i] != '' else 'none'
        result_list[server[0]] = server_dict

    return jsonify({'result': result_list}), 200

@app.route('/accept_user/<username>')
@auth.verify
def accept_user(user, username):
    if not user:
        return jsonify({"message": "no permission"}), 403
    if not user['role'] == "admin":
        return jsonify({"message": "no permission"}), 403
    user_accept = User.query.filter_by(username=username).first()
    if not user_accept:
        return jsonify({"message": "not found"}), 404
    
    user_accept.is_accept = True
    db_session.commit()
    
    return jsonify({'message': 'success'}), 200

@app.route('/delete_user/<username>')
@auth.verify
def delete_user(user, username):
    if not user:
        return jsonify({"message": "no permission"}), 403
    if not user['role'] == "admin":
        return jsonify({"message": "no permission"}), 403
    user_delete = User.query.filter_by(username=username).first()
    if not user_delete:
        return jsonify({"message": "not found"}), 404
    
    #TODO: close user pod
    
    delete_q = UserServer.__table__.delete().where(UserServer.user_id == user_delete.id)
    db_session.execute(delete_q)
    db_session.delete(user_delete)
    db_session.commit()

    return jsonify({'message': 'success'}), 200

@app.route('/change_server/<username>/<server_name>')
@auth.verify
def change_server(user, username, server_name):
    if not user:
        return jsonify({"message": "no permission"}), 403
    if not user['role'] == "admin" and user['username'] != username:
        return jsonify({"message": "no permission"}), 403
    if not user['is_accept']:
        return jsonify({"message": "no permission"}), 403
    
    user_change = User.query.filter_by(username=username).first()
    if not user_change:
        return jsonify({"message": "not found"}), 404
    if not user_change.is_accept:
        return jsonify({"message": "no permission"}), 403
    if not user_change.state == 'offline':
        return jsonify({"message": "no permission"}), 403
    
    server = ServerOption.query.filter_by(name=server_name).first()
    if not server:
        return jsonify({"message": "not found"}), 404
    
    userserver = UserServer.query.filter_by(user_id=user_change.id, server_id=server.id).first()
    if not userserver:
        return jsonify({"message": "no permission"}), 403
    
    user_change.current_server = server.id
    db_session.commit()

    return jsonify({'message': 'success'}), 200

@app.route('/add_server_user/<username>/<server_name>')
@auth.verify
def add_server_user(user, username, server_name):
    if not user:
        return jsonify({"message": "no permission"}), 403
    if not user['role'] == "admin":
        return jsonify({"message": "no permission"}), 403
    
    user_change = User.query.filter_by(username=username).first()
    if not user_change:
        return jsonify({"message": "not found"}), 404
    
    server = ServerOption.query.filter_by(name=server_name).first()
    if not server:
        return jsonify({"message": "not found"}), 404
    
    userserver = UserServer.query.filter_by(user_id=user_change.id, server_id=server.id).first()
    if not userserver:
        userserver = UserServer(user_id=user_change.id, server_id=server.id)
        db_session.add(userserver)
        db_session.commit()

    return jsonify({'message': 'success'}), 200

@app.route('/delete_server_user/<username>/<server_name>')
@auth.verify
def delete_server_user(user, username, server_name):
    if not user:
        return jsonify({"message": "no permission"}), 403
    if not user['role'] == "admin":
        return jsonify({"message": "no permission"}), 403
    
    user_change = User.query.filter_by(username=username).first()
    if not user_change:
        return jsonify({"message": "not found"}), 404
    
    server = ServerOption.query.filter_by(name=server_name).first()
    if not server:
        return jsonify({"message": "not found"}), 404
    
    userserver = UserServer.query.filter_by(user_id=user_change.id, server_id=server.id).first()
    available_server = UserServer.query.filter_by(user_id=user_change.id).first()
    if not userserver:
        return jsonify({"message": "not found"}), 404
    
    if server.id == user_change.current_server and available_server:
        user_change.current_server = available_server.server_id
    elif server.id == user_change.current_server:
        user_change.current_server = 1

    db_session.delete(userserver)
    db_session.commit()

    return jsonify({'message': 'success'}), 200

@app.route('/start_server/<username>')
@auth.verify
def start_server(user, username):
    if not user:
        return jsonify({"message": "no permission"}), 403
    if not user['role'] == "admin" and user['username'] != username:
        return jsonify({"message": "no permission"}), 403
    if not user['is_accept']:
        return jsonify({"message": "no permission"}), 403
    
    user_change = User.query.filter_by(username=username).first()
    if not user_change:
        return jsonify({"message": "not found"}), 404
    if not user_change.is_accept:
        return jsonify({"message": "no permission"}), 403
    if not user_change.state == 'offline':
        return jsonify({"message": "no permission"}), 403
    
    user_change.state = 'running'

    #TODO: thread start server with current server option and send event if success change state to online else to ofline
    # user_change.current_server
    # user_change.state
    # save pod ip to user_change.ip
    user_change.server_ip = '127.0.0.1'

    db_session.commit()

    return jsonify({'message': 'success'}), 200


@app.route('/stop_server/<username>')
@auth.verify
def stop_server(user, username):
    if not user:
        return jsonify({"message": "no permission"}), 403
    if not user['role'] == "admin" and user['username'] != username:
        return jsonify({"message": "no permission"}), 403
    if not user['is_accept']:
        return jsonify({"message": "no permission"}), 403
    
    user_change = User.query.filter_by(username=username).first()
    if not user_change:
        return jsonify({"message": "not found"}), 404
    if not user_change.is_accept:
        return jsonify({"message": "no permission"}), 403
    if not user_change.state == 'running':
        return jsonify({"message": "no permission"}), 403
    
    user_change.state = 'offline'

    #TODO: thread stop server with current server option and send event and change state to ofline
    # user_change.current_server
    # user_change.state
    # clear user pod ip
    user_change.ip = ""

    db_session.commit()

    return jsonify({'message': 'success'}), 200

@sock.route('/user/<username>/')
@sock.route('/user/<username>/<path:path>')
@auth.verify
def handle_socket(user, ws, username, path=None):
    if not user:
        return jsonify({"message": "no permission"}), 403
    if not user['role'] == "admin" and user['username'] != username:
        return jsonify({"message": "no permission"}), 403
    if not user['is_accept']:
        return jsonify({"message": "no permission"}), 403
    
    user_change = User.query.filter_by(username=username).first()
    if not user_change:
        return jsonify({"message": "not found"}), 404
    if not user_change.is_accept:
        return jsonify({"message": "no permission"}), 403
    if not user_change.state == 'running':
        return jsonify({"message": "no permission"}), 403
    
    params_str = '/?'
    for key, value in request.args.items():
        params_str += f'{key}={value}&'
    params_str = params_str.rstrip('&')

    headers = dict(request.headers)

    wss = create_connection('ws://' + user_change.server_ip + ":8443/" +  (path if path else '') + params_str, cookie=headers['Cookie'])

    p = threading.Thread(target=producer, args=(ws,wss))
    c = threading.Thread(target=consumer, args=(ws,wss))

    p.start()
    c.start()

    while p.is_alive() or c.is_alive():
        continue
    
    ws.close()
    p.join()
    c.join()

@app.route('/user/<username>/')
@app.route('/user/<username>/<path:path>')
@auth.verify
def proxy(user, username, path=None):
    if not user:
        return jsonify({"message": "no permission"}), 403
    if not user['role'] == "admin" and user['username'] != username:
        return jsonify({"message": "no permission"}), 403
    if not user['is_accept']:
        return jsonify({"message": "no permission"}), 403
    
    user_change = User.query.filter_by(username=username).first()
    if not user_change:
        return jsonify({"message": "not found"}), 404
    if not user_change.is_accept:
        return jsonify({"message": "no permission"}), 403
    if not user_change.state == 'running':
        return jsonify({"message": "no permission"}), 403
    
    url = user_change.server_ip + ":8443/" + (path if path else '')

    r = make_request(url, request.method, dict(request.headers), request.form)
    headers = dict(r.raw.headers)
    def generate():
        for chunk in r.raw.stream(decode_content=False):
            yield chunk
    out = Response(generate(), headers=headers)
    out.status_code = r.status_code
    return out



def make_request(url, method, headers={}, data=None):
    url = 'http://%s' % url
    return requests.request(method, url, params=request.args, stream=True, headers=headers, allow_redirects=False, data=data, cookies=request.cookies)


def producer(ws, wss):
    while wss.connected and ws.connected:
        data = ws.receive()
        if data is None:
            wss.close()
            ws.close()
            break
        wss.send(data)
    return


def consumer(ws, wss):
    while wss.connected and ws.connected:
        response = wss.recv()
        if response is None:
            wss.close()
            ws.close()
            break
        ws.send(response)
    return


def migrate():
    for server_option in config_file['initServerOptions']:
        server = ServerOption.query.filter_by(name=server_option['name']).first()
        if server:
            continue
        server_option_entity = ServerOption(
                    name = server_option['name'], 
                    image = server_option['image'], 
                    docker_image = server_option['docker_image'], 
                    cpu = server_option['cpu'],
                    ram = server_option['ram'],
                    drive = server_option['drive'],
                    gpu = server_option['gpu'],
                    color = server_option['color'])
        db_session.add_all(server_option_entity)
        db_session.commit()

if __name__ == '__main__': 
    app.run("0.0.0.0", 5000, debug=False)