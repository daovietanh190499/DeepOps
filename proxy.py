"""
A simple proxy server, based on original by gear11:
https://gist.github.com/gear11/8006132
Modified from original to support both GET and POST, status code passthrough, header and form data passthrough.
Usage: http://hostname:port/p/(URL to be proxied, minus protocol)
For example: http://localhost:8080/p/www.google.com
"""
import re
from urllib.parse import urlparse, urlunparse
from flask import Flask, render_template, request, abort, Response, redirect
import requests
import threading
from flask_sock import Sock
from websocket import create_connection

app = Flask(__name__.split('.')[0])
CHUNK_SIZE = 1024
sock = Sock(app)


@app.route('/<path:url>', methods=["GET", "POST"])
def root(url):
    referer = request.headers.get('referer')
    if not referer:
        return Response("Relative URL sent without a a proxying request referal. Please specify a valid proxy host (/p/url)", 400)
    proxy_ref = proxied_request_info(referer)
    host = proxy_ref[0]
    redirect_url = "/p/%s/%s%s" % (host, url, ("?" + request.query_string.decode('utf-8') if request.query_string else ""))
    return redirect(redirect_url)


@app.route('/p/<path:url>')
def proxy(url):
    url_parts = urlparse('%s://%s' % (request.scheme, url))
    if url_parts.path == "":
        parts = urlparse(request.url)
        return redirect(urlunparse(parts._replace(path=parts.path+'/')))

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

    referer = request.headers.get('referer')
    if referer:
        proxy_ref = proxied_request_info(referer)
        headers.update({ "referer" : "http://%s/%s" % (proxy_ref[0], proxy_ref[1])})
    
    return requests.request(method, url, params=request.args, stream=True, headers=headers, allow_redirects=False, data=data, cookies=request.cookies)


def proxied_request_info(proxy_url):
    parts = urlparse(proxy_url)
    if not parts.path:
        return None
    elif not parts.path.startswith('/p/'):
        return None
    matches = re.match('^/p/([^/]+)/?(.*)', parts.path)
    proxied_host = matches.group(1)
    proxied_path = matches.group(2) or '/'
    proxied_tail = urlunparse(parts._replace(scheme="", netloc="", path=proxied_path))
    return [proxied_host, proxied_tail]


@sock.route('/p/<path:path>')
def handle_socket(ws, path):
    params_str = '/?'
    for key, value in request.args.items():
        params_str += f'{key}={value}&'
    params_str = params_str.rstrip('&')

    headers = dict(request.headers)

    wss = create_connection('ws://' + path + params_str, cookie=headers['Cookie'])

    p = threading.Thread(target=producer, args=(ws,wss))
    c = threading.Thread(target=consumer, args=(ws,wss))

    p.start()
    c.start()

    while p.is_alive() or c.is_alive():
        continue

    p.join()
    c.join()


def producer(ws, wss):
    while True:
        data = ws.receive()
        if data is None:
            wss.close()
            break
        wss.send(data)
    return


def consumer(ws, wss):
    while wss.connected:
        response = wss.recv()
        ws.send(response)
    return


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
