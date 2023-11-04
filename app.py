from aiohttp import web
from aiohttp import client
import aiohttp
import asyncio
import pprint
import ssl
import time

import aiohttp_jinja2
import jinja2

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

import yaml
from furl import furl
import requests
import json
import uuid
from functools import wraps

import traceback

from spawners.k8s.kubespawn import delete_pv, delete_pvc, delete_server, create_pv, create_pvc, create_server, get_server, get_pv, get_pvc, get_servers
from fileserver.controller import create_folder

with open("/etc/dohub/config.yaml", 'r') as stream:
    config_file = yaml.safe_load(stream)

DATABASE_URI = 'sqlite:////mnt/database/dohub.db'
SECRET_KEY = 'dohub'
DEBUG = True

# Set these values
GITHUB_CLIENT_ID = config_file['githubOauth']['GITHUB_CLIENT_ID']
GITHUB_CLIENT_SECRET = config_file['githubOauth']['GITHUB_CLIENT_SECRET']

app = web.Application(client_max_size=200*1024**2)

aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))

# setup sqlalchemy
engine = create_engine(DATABASE_URI)
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

    def __init__(self, db=None):
        self.db = db
        self.init_app()

    def init_app(self):
        self.client_id = GITHUB_CLIENT_ID
        self.client_secret = GITHUB_CLIENT_SECRET
        self.base_url = self.BASE_URL
        self.auth_url = self.BASE_AUTH_URL
        # self.session = requests.session()

    def oauth_login(self):
        params = {
            'client_id': self.client_id,
            'scope': 'read:user',
            'state': 'An unguessable random string.',
            'allow_signup': 'true'
        }
        url = furl(self.auth_url + 'authorize').set(params)
        url = str(url)
        raise web.HTTPFound(location=url)
    
    def handle_callback(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            code = args[0].query.get('code')
            if not code:
                resp = web.HTTPError(text="No permission")
                resp.set_status(403)
                return resp

            payload = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'state': 'An unguessable random string.'
            }
            r = requests.post(self.BASE_AUTH_URL + 'access_token', json=payload, headers={'Accept': 'application/json'})
            if not 'access_token' in json.loads(r.text):
                resp = web.HTTPError(text="No permission")
                resp.set_status(403)
                return resp
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
            try:
                access_key = args[0].cookies['user_access_key']
            except:
                access_key = None
            if not access_key:
                user = None
            else:
                user = User.query.filter_by(access_key=access_key).first()
                if user:
                    user = user.__dict__
            return f(*((user,) + args), **kwargs)
        return decorated
        
    def login_user(self, user, request):
        access_key = uuid.uuid4()
        user.access_key = str(access_key)
        db_session.commit()
        location = request.app.router['index'].url_for()
        response = web.HTTPSeeOther(location=location)
        response.cookies['user_access_key'] = user.access_key
        return response

    def logout_user(self, request):
        location = request.app.router['index'].url_for()
        response = web.HTTPSeeOther(location=location)
        response.cookies['user_access_key'] = ''
        return response

auth = GitAuth(db_session)

async def handle_404(request, ex: web.HTTPException):
    return aiohttp_jinja2.render_template('page-error.html', request, {'code': 404, 'error': ex.text})

async def handle_403(request, ex: web.HTTPException):
    return aiohttp_jinja2.render_template('page-error.html', request, {'code': 403, 'error': ex.text})

async def handle_500(request, ex: web.HTTPException):
    return aiohttp_jinja2.render_template('page-error.html', request, {'code': 500, 'error': ex.text})


def create_error_middleware(overrides):
    @web.middleware
    async def error_middleware(request, handler):
        try:
            Base.metadata.create_all(bind=engine)
            migrate()
            resp = await handler(request)
            db_session.remove()
            return resp
        except web.HTTPException as ex:
            override = overrides.get(ex.status)
            if override:
                resp = await override(request, ex)
                resp.set_status(ex.status)
                return resp

            raise
        except Exception as e:
            resp = await overrides[500](request, web.HTTPError(text=traceback.format_exc()))
            resp.set_status(500)
            return resp

    return error_middleware


def setup_middlewares(app):
    error_middleware = create_error_middleware({
        403: handle_403,
        404: handle_404,
        500: handle_500,
    })
    app.middlewares.append(error_middleware)

setup_middlewares(app)

@auth.handle_callback
async def authorized(user, request):
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

    return auth.login_user(user_, request)

@auth.verify
async def login(user, request):
    if user is None:
        return auth.oauth_login()
    else:
        location = request.app.router['index'].url_for()
        raise web.HTTPFound(location=location)
    
async def logout(request):
    return auth.logout_user(request)

@auth.verify
async def index(user, request):
    if user and user['state'] == 'running':
        raise web.HTTPFound(location="/user/" + user["username"] + "/main/")
    else:
        location = request.app.router['hub'].url_for()
        raise web.HTTPFound(location=location)

@aiohttp_jinja2.template('index.html') 
@auth.verify
async def hub(user, request):
    return {"user": user}

@auth.verify
async def user_state(user, request):
    if not user:
        return web.json_response({"message": "no permission"}, status=403)
    del user['_sa_instance_state']
    all_servers = db_session.query(ServerOption.name) \
            .filter(ServerOption.id == UserServer.server_id) \
            .filter(UserServer.user_id == user['id']) \
            .all()
    current_server = db_session.query(ServerOption.name).filter(ServerOption.id == user['current_server']).first()
    all_servers = [db[0] for db in all_servers]
    user['server_list'] = all_servers
    user['current_server'] = current_server[0]
    user['server_log'] = get_server(user['username'])
    return web.json_response({"result": user}, status=200)

@auth.verify
def all_user(user, request):
    if not user:
        return web.json_response({"message": "no permission"}, status=403)
    if not user['role'] == "admin":
        return web.json_response({"message": "no permission"}, status=403)
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
        user_dict['server_log'] = get_server(user[1])
        result_list.append(user_dict)
    
    return web.json_response({"result": result_list}, status=200)

async def all_server(request):
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

    return web.json_response({"result": result_list}, status=200)

@auth.verify
async def accept_user(user, request):
    username = request.match_info.get('username', None)
    if not user:
        return web.json_response({"message": "no permission"}, status=403)
    if not user['role'] == "admin":
        return web.json_response({"message": "no permission"}, status=403)
    user_accept = User.query.filter_by(username=username).first()
    if not user_accept:
        return web.json_response({"message": "not found"}, status=404)
    
    user_accept.is_accept = True
    db_session.commit()
    
    return web.json_response({"message": "success"}, status=200)

@auth.verify
async def delete_user(user, request):
    username = request.match_info.get('username', None)
    if not user:
        return web.json_response({"message": "no permission"}, status=403)
    if not user['role'] == "admin":
        return web.json_response({"message": "no permission"}, status=403)
    user_delete = User.query.filter_by(username=username).first()
    if not user_delete:
        return web.json_response({"message": "not found"}, status=404)
    
    stop_server_pipline(user_delete)
    
    delete_q = UserServer.__table__.delete().where(UserServer.user_id == user_delete.id)
    db_session.execute(delete_q)
    db_session.delete(user_delete)
    db_session.commit()

    return web.json_response({"message": "success"}, status=200)

@auth.verify
async def change_server(user, request):
    username = request.match_info.get('username', None)
    server_name = request.match_info.get('server_name', None)
    if not user:
        return web.json_response({"message": "no permission"}, status=403)
    if not user['role'] == "admin" and user['username'] != username:
        return web.json_response({"message": "no permission"}, status=403)
    if not user['is_accept']:
        return web.json_response({"message": "no permission"}, status=403)
    
    user_change = User.query.filter_by(username=username).first()
    if not user_change:
        return web.json_response({"message": "not found"}, status=404)
    if not user_change.is_accept:
        return web.json_response({"message": "no permission"}, status=403)
    if not user_change.state == 'offline':
        return web.json_response({"message": "no permission"}, status=403)
    
    server = ServerOption.query.filter_by(name=server_name).first()
    if not server:
        return web.json_response({"message": "not found"}, status=404)
    
    userserver = UserServer.query.filter_by(user_id=user_change.id, server_id=server.id).first()
    if not userserver:
        return web.json_response({"message": "no permission"}, status=403)
    
    user_change.current_server = server.id
    db_session.commit()

    return web.json_response({"message": "success"}, status=200)

@auth.verify
async def change_role(user, request):
    username = request.match_info.get('username', None)
    role = request.match_info.get('role', None)
    if not user:
        return web.json_response({"message": "no permission"}, status=403)
    if not user['role'] == "admin" or user['username'] == username:
        return web.json_response({"message": "no permission"}, status=403)
    if not user['is_accept']:
        return web.json_response({"message": "no permission"}, status=403)
    
    user_change = User.query.filter_by(username=username).first()
    if not user_change:
        return web.json_response({"message": "not found"}, status=404)
    if not user_change.is_accept:
        return web.json_response({"message": "no permission"}, status=403)
    
    if not (role in ['admin', 'normal_user']):
        return web.json_response({"message": "no permission"}, status=403)
    
    user_change.role = role
    db_session.commit()

    return web.json_response({"message": "success"}, status=200)

@auth.verify
async def add_server_user(user, request):
    username = request.match_info.get('username', None)
    server_name = request.match_info.get('server_name', None)
    if not user:
        return web.json_response({"message": "no permission"}, status=403)
    if not user['role'] == "admin":
        return web.json_response({"message": "no permission"}, status=403)
    
    user_change = User.query.filter_by(username=username).first()
    if not user_change:
        return web.json_response({"message": "not found"}, status=404)
    
    server = ServerOption.query.filter_by(name=server_name).first()
    if not server:
        return web.json_response({"message": "not found"}, status=404)
    
    userserver = UserServer.query.filter_by(user_id=user_change.id, server_id=server.id).first()
    if not userserver:
        userserver = UserServer(user_id=user_change.id, server_id=server.id)
        db_session.add(userserver)
        db_session.commit()

    return web.json_response({"message": "success"}, status=200)

@auth.verify
async def delete_server_user(user, request):
    username = request.match_info.get('username', None)
    server_name = request.match_info.get('server_name', None)
    if not user:
        return web.json_response({"message": "no permission"}, status=403)
    if not user['role'] == "admin":
        return web.json_response({"message": "no permission"}, status=403)
    
    user_change = User.query.filter_by(username=username).first()
    if not user_change:
        return web.json_response({"message": "not found"}, status=404)
    
    server = ServerOption.query.filter_by(name=server_name).first()
    if not server:
        return web.json_response({"message": "not found"}, status=404)
    
    userserver = UserServer.query.filter_by(user_id=user_change.id, server_id=server.id).first()
    available_server = UserServer.query.filter_by(user_id=user_change.id).first()
    if not userserver:
        return web.json_response({"message": "not found"}, status=404)
    
    if server.id == user_change.current_server and available_server:
        user_change.current_server = available_server.server_id
    elif server.id == user_change.current_server:
        user_change.current_server = 1

    db_session.delete(userserver)
    db_session.commit()

    return web.json_response({"message": "success"}, status=200)

def start_server_pipline(user, server):
    username = user.username
    config = {
        'username': user.username,
        'cpu': server.cpu,
        'max_cpu': server.cpu*1.5,
        'max_ram': str(int(server.ram[:-1])*1.5) + 'G',
        'ram': server.ram,
        'gpu_type': 'nvidia.com/' + (server.gpu.split(':')[0] if ':' in server.gpu else server.gpu),
        'gpu_quantity': int(server.gpu.split(':')[1]) if ':' in server.gpu else 1,
        'not_use_gpu': not server.gpu or server.gpu == '' or server.gpu == 'null' or server.gpu == "",
        'image': server.docker_image,
        'path': config_file['nasPath'],
        'file_server': config_file['nasAddresses'][config_file['nasIndex']],
        'file_server_index': config_file['nasIndex'],
        'password': user.access_password,
        'defaultPort': config_file['defaultPort']
    }
    if config_file['spawner'] == 'k8s':
        try:
            create_folder(config)
        except:
            return web.json_response({'message': 'action create folder failed'}, status=500)
    try:
        res = get_pv(user.username)
    except:
        res = None
    if not res:
        res = create_pv(config)
        if not res:
            return web.json_response({'message': 'action create persistent volume failed'}, status=500)
    try:
        res = get_pvc(user.username)
    except:
        res = None
    if not res:
        res = create_pvc(config)
        if not res:
            return web.json_response({'message': 'action create persistent volume claim failed'}, status=500)
    try:
        res = get_server(user.username)
    except:
        res = None
    if not res or not 'state' in res or res['state']['message'] == 'Idle':
        res = create_server(config)
        if not res:
            return web.json_response({'message': 'action create server failed'}, status=500)

    user.state = 'pending_start'
    user.server_ip = ''
    db_session.commit()
    
    async def thread_start_pending():
        res = None
        count = 0
        while (not res or 'ip' not in res or not res['ip']) and count < 100:
            count += 1
            try:
                res = get_server(username)
            except:
                continue
            if res and 'ip' in res and res['ip']:
                user_change = User.query.filter_by(username=username).first()
                user_change.state = 'running'
                user_change.server_ip = res['ip']
                db_session.commit()
                break
            await asyncio.sleep(1)
        user_change = User.query.filter_by(username=username).first()
        if not user_change.server_ip or user_change.server_ip == '':
            user_change.state = 'offline'
            db_session.commit()
        return
    
    loop = asyncio.get_event_loop()
    loop.create_task(thread_start_pending())

    return web.json_response({'message': 'success'}, status=200)

def stop_server_pipline(user):
    username = user.username
    try:
        res = delete_server(user.username)
    except:
        return web.json_response({'message': 'action failed'}, status=500)
    if not res:
        return web.json_response({'message': 'action failed'}, status=500)
    
    user.state = 'pending_stop'
    db_session.commit()
    
    async def thread_stop_pending():
        res = {'ip': 'available'}
        count = 0
        while res and 'ip' in res and res['ip'] and count < 100:
            count += 1
            try:
                res = get_server(username)
            except:
                user_change = User.query.filter_by(username=username).first()
                user_change.state = 'offline'
                user_change.server_ip = ''
                db_session.commit()
                res['ip'] = None
                break
            if not res or not 'ip' in res or not res['ip']:
                user_change = User.query.filter_by(username=username).first()
                user_change.state = 'offline'
                user_change.server_ip = ''
                db_session.commit()
                res['ip'] = None
                break
            await asyncio.sleep(1)
        user_change = User.query.filter_by(username=username).first()
        if user_change.server_ip and user_change.server_ip != '':
            user_change.state = 'running'
            db_session.commit()
        else:
            user_change = User.query.filter_by(username=username).first()
            user_change.state = 'offline'
            user_change.server_ip = ''
            db_session.commit()
        return
    
    loop = asyncio.get_event_loop()
    loop.create_task(thread_stop_pending())

    return web.json_response({'message': 'success'}, status=200)

@auth.verify
async def start_server(user, request):
    username = request.match_info.get('username', None)
    if not user:
        return web.json_response({"message": "no permission"}, status=403)
    if not user['role'] == "admin" and user['username'] != username:
        return web.json_response({"message": "no permission"}, status=403)
    if not user['is_accept']:
        return web.json_response({"message": "no permission"}, status=403)
    
    user_change = User.query.filter_by(username=username).first()
    if not user_change:
        return web.json_response({"message": "not found"}, status=404)
    if not user_change.is_accept:
        return web.json_response({"message": "no permission"}, status=403)
    if not user['role'] == "admin":
        if not (user_change.state == 'running' and user_change.state == 'pending_start'):
            return web.json_response({"message": "no permission"}, status=403)
    
    server = ServerOption.query.filter_by(id=user_change.current_server).first()
    if not server:
        return web.json_response({"message": "not found"}, status=404)

    return start_server_pipline(user=user_change, server=server)


@auth.verify
async def stop_server(user, request):
    username = request.match_info.get('username', None)
    if not user:
        return web.json_response({"message": "no permission"}, status=403)
    if not user['role'] == "admin" and user['username'] != username:
        return web.json_response({"message": "no permission"}, status=403)
    if not user['is_accept']:
        return web.json_response({"message": "no permission"}, status=403)
    
    user_change = User.query.filter_by(username=username).first()
    if not user_change:
        return web.json_response({"message": "not found"}, status=404)
    if not user_change.is_accept:
        return web.json_response({"message": "no permission"}, status=403)
    if not user['role'] == "admin":
        if not (user_change.state == 'running' or user_change.state == 'pending_start'):
            return web.json_response({"message": "no permission"}, status=403)
    
    return stop_server_pipline(user_change)

async def handler_proxy(req):
    timeout = aiohttp.ClientTimeout()
    proxyPath = req.match_info.get('proxyPath','')
    port_str = req.match_info.get('port', config_file['defaultPort'])
    port = req.match_info.get('port', config_file['defaultPort'])
    username = req.match_info.get('username', None)

    user_change = User.query.filter_by(username=username).first()
    if config_file['spawner'] == 'local' or config_file['spawner'] == 'k8s':
        server_domain = user_change.server_ip
    else:
        server_domain = f'dohub-{username}'

    port_str = str(config_file['defaultPort']) if port_str == 'main' else port_str

    # if port_str == '1337':
    #     proxyPath = f'user/{username}/{port}/{proxyPath}'
    
    reqH = req.headers.copy()
    baseUrl = f'http://{server_domain}:{port_str}/{proxyPath}'

    if reqH['connection'] == 'Upgrade' and reqH['upgrade'] == 'websocket' and req.method == 'GET':
      ws_server = web.WebSocketResponse(max_msg_size=0)
      await ws_server.prepare(req)
      client_session = aiohttp.ClientSession(cookies=req.cookies, timeout=timeout)
      async with client_session.ws_connect(
        baseUrl,
        max_msg_size=0
      ) as ws_client:
        async def wsforward(ws_from,ws_to):
          async for msg in ws_from:
            mt = msg.type
            md = msg.data
            if mt == aiohttp.WSMsgType.TEXT:
              await ws_to.send_str(md)
            elif mt == aiohttp.WSMsgType.BINARY:
              await ws_to.send_bytes(md)
            elif mt == aiohttp.WSMsgType.PING:
              await ws_to.ping()
            elif mt == aiohttp.WSMsgType.PONG:
              await ws_to.pong()
            elif ws_to.closed:
              await ws_to.close(code=ws_to.close_code,message=msg.extra)
            else:
              raise ValueError('unexpecte message type: %s',pprint.pformat(msg))

        finished, unfinished = await asyncio.wait([wsforward(ws_server,ws_client), wsforward(ws_client,ws_server)], return_when=asyncio.FIRST_COMPLETED)

        return ws_server
    else:
      user_change.last_activity = time.time() * 1000
      db_session.commit()
      async with client.request(
        method = req.method,
        url = baseUrl,
        headers = reqH,
        params = req.query,
        allow_redirects = False,
        data = await req.read()
      ) as res:
        headers = res.headers.copy()
        body = await res.read()
        headers.pop('Transfer-Encoding', None)
        headers.pop('Content-Encoding', None)
        if res.status == 302:
            if headers['Location'][0] == '.':
                location = headers['Location'][1:]
            elif headers['Location'][0] == '/':
                location = headers['Location']
            else:
                location = '/' + headers['Location']
            headers['Location'] = f'/user/{username}/{port}' + location
        return web.Response(
            headers = headers,
            status = res.status,
            body = body
        )

app.router.add_route('*', '/github-callback', authorized, name='github-callback')
app.router.add_route('*', '/login', login, name='login')
app.router.add_route('*', '/logout', logout, name='logout')
app.router.add_route('*', '/', index, name='index')
app.router.add_route('*', '/hub', hub, name='hub')
app.router.add_route('*', '/user_state', user_state, name='user-state')
app.router.add_route('*', '/all_users', all_user, name='all-user')
app.router.add_route('*', '/all_servers', all_server, name='all-servers')
app.router.add_route('*', '/accept_user/{username}', accept_user)
app.router.add_route('*', '/delete_user/{username}', delete_user)
app.router.add_route('*', '/change_server/{username}/{server_name}', change_server)
app.router.add_route('*', '/change_role/{username}/{role}', change_role)
app.router.add_route('*', '/add_server_user/{username}/{server_name}', add_server_user)
app.router.add_route('*', '/delete_server_user/{username}/{server_name}', delete_server_user)
app.router.add_route('*', '/start_server/{username}', start_server)
app.router.add_route('*', '/stop_server/{username}', stop_server)
app.router.add_route('*', '/user/{username}/{port}/{proxyPath:.*}', handler_proxy)
app.add_routes([web.static('/static', 'static')])

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
        db_session.add(server_option_entity)
        db_session.commit()

if __name__ == "__main__":
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain("/etc/dohub/cert.pem", "/etc/dohub/key.pem")
    web.run_app(app, port=5000, ssl_context=ssl_context)
