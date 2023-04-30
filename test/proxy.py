"""
A simple proxy server, based on original by gear11:
https://gist.github.com/gear11/8006132
Modified from original to support both GET and POST, status code passthrough, header and form data passthrough.
Usage: http://hostname:port/p/(URL to be proxied, minus protocol)
For example: http://localhost:5000/p/www.google.com
"""
import re
from urllib.parse import urlparse, urlunparse
from flask import Flask, render_template, request, abort, Response, redirect
import requests
import threading
from flask_sock import Sock
from websocket import create_connection, WebSocketApp

from pubsub import pub

app = Flask(__name__.split('.')[0])
CHUNK_SIZE = 1024
sock = Sock(app)


@sock.route('/user/<username>/<port>/', methods=['GET', 'HEAD', 'OPTIONS'])
@sock.route('/user/<username>/<port>/<path:path>', methods=['GET', 'HEAD', 'OPTIONS'])
def handle_socket(ws, port, username, path=None):
    
    params_str = '/?'
    for key, value in request.args.items():
        params_str += f'{key}={value}&'
    params_str = params_str.rstrip('&')

    headers = dict(request.headers)

    # if config_file['spawner'] == 'local' or config_file['spawner'] == 'k8s':
    #     server_domain = user_change.server_ip
    # else:
    #     server_domain = f'dohub-{username}'
    server_domain = "10.32.0.7"

    port_str = str(port)

    def on_message(wsss, message):
        ws.send(message)

    wss = WebSocketApp('ws://' + server_domain + ":" + port_str + "/" +  (path if path else '') + params_str, cookie=headers['Cookie'], on_message=on_message)
    
    run_wss = threading.Thread(target=wss.run_forever)

    run_wss.start()
    
    while True:
        message = ws.receive()
        wss.send(message)

    
    # wss = create_connection('ws://' + server_domain + ":" + port_str + "/" +  (path if path else '') + params_str, cookie=headers['Cookie'])

    # receiveClient = threading.Thread(target=producer, args=(ws, wss, username + '-receiveClient',))
    # receiveServer = threading.Thread(target=consumer, args=(ws, wss, username + '-receiveServer',))
    # pub.subscribe(handle_send, username + '-receiveClient')
    # pub.subscribe(handle_send, username + '-receiveServer')

    # receiveClient.start()
    # receiveServer.start()

    # while receiveClient.is_alive() or receiveServer.is_alive():
    #     continue
    
    # ws.close()
    # receiveClient.join()
    # receiveServer.join()


@app.route('/user/<username>/<port>/', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD'])
@app.route('/user/<username>/<port>/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD'])

def proxy(port, username, path=None):

    # if config_file['spawner'] == 'local' or config_file['spawner'] == 'k8s':
    #     user_change = User.query.filter_by(username=username).first()
    #     server_domain = user_change.server_ip
    # else:
    #     server_domain = f'dohub-{username}'

    server_domain = "10.32.0.7"

    port_str = str(port)
    
    url = server_domain + ":" + port_str + "/" + (path if path else '')

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

def producer(ws, wss, topic):
    while wss.connected and ws.connected:
        try:
            data = ws.receive()
        except:
            data = None
        if data is None:
            wss.close()
            ws.close()
            break
        pub.sendMessage(topic, wss=wss, data=data)
    return

def handle_send(wss, data=None):
    if wss.connected:
        wss.send(data)
    return

def consumer(ws, wss, topic):
    while wss.connected and ws.connected:
        response = wss.recv()
        if response is None:
            wss.close()
            ws.close()
            break
        pub.sendMessage(topic, wss=ws, data=response)
    return

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)
