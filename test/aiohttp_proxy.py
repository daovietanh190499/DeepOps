from aiohttp import web
from aiohttp import client
import aiohttp
import asyncio
import logging
import pprint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handler(req):
    proxyPath = req.match_info.get('proxyPath','no proxyPath placeholder defined')
    server_domain = "10.32.0.7"
    port_str = req.match_info.get('port','8443')
    username = req.match_info.get('username','no Username placeholder defined')
    reqH = req.headers.copy()
    baseUrl = f'http://{server_domain}:{port_str}/{proxyPath}'

    if reqH['connection'] == 'Upgrade' and reqH['upgrade'] == 'websocket' and req.method == 'GET':
      ws_server = web.WebSocketResponse()
      await ws_server.prepare(req)
      client_session = aiohttp.ClientSession(cookies=req.cookies)
      async with client_session.ws_connect(
        baseUrl,
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
        return web.Response(
            headers = headers,
            status = res.status,
            body = body
        )

app = web.Application()
app.router.add_route('*', '/user/{username}/{port}/{proxyPath:.*}', handler)
web.run_app(app, port=8000)