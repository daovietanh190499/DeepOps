from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask
from starlette.websockets import WebSocketState

import httpx
from httpx import AsyncClient

import threading

import uvicorn

app = FastAPI()

import asyncio

import functools

import websockets
from fastapi import WebSocket

from contextlib import closing

@app.api_route('/user/{username}/{port}/{path:path}', methods=['GET', 'POST'])
async def reverse_proxy(request: Request, username: str, port: str, path: str):
    # if config_file['spawner'] == 'local' or config_file['spawner'] == 'k8s':
    #     user_change = User.query.filter_by(username=username).first()
    #     server_domain = user_change.server_ip
    # else:
    #     server_domain = f'dohub-{username}'
    server_domain = '10.32.0.7'

    port_str = str(port)
    
    url = server_domain + ":" + port_str

    HTTP_SERVER = AsyncClient(base_url=f"http://{url}")
    url = httpx.URL(path=path, query=request.url.query.encode("utf-8"))
    rp_req = HTTP_SERVER.build_request(
        request.method, url, headers=request.headers.raw, content=await request.body()
    )
    rp_resp = await HTTP_SERVER.send(rp_req, stream=True)
    return StreamingResponse(
        rp_resp.aiter_raw(),
        status_code=rp_resp.status_code,
        headers=rp_resp.headers,
        background=BackgroundTask(rp_resp.aclose),
    )


@app.websocket('/user/{username}/{port}/{path:path}')
async def websocket_a(ws: WebSocket, username: str, port: str, path: str):

    server_domain = '10.32.0.7'

    port_str = str(port)

    query_params = ws.query_params

    await ws.accept()
    async with websockets.connect(f'ws://{server_domain}:{port_str}/{path}?{query_params}', extra_headers={"Cookie": ws.headers['cookie']}) as ws_b_client:
        loop = asyncio.get_event_loop()

        async def forward():
            while ws.client_state != WebSocketState.DISCONNECTED:
                try:
                    data = await ws.receive_bytes()
                    await ws_b_client.send(data)
                except Exception as e:
                    print("ERR1")
                    await ws_b_client.close()
                    await ws.close()
                    break

        async def reverse(): 
            while ws.client_state != WebSocketState.DISCONNECTED:
                try:
                    data = await ws_b_client.recv()
                    await ws.send_bytes(data)
                except Exception as e:
                    print("ERR2", e)
                    await ws_b_client.close()
                    await ws.close()
                    break

        fwd = loop.create_task(forward())
        rev = loop.create_task(reverse())

        await asyncio.gather(fwd, rev)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, ws_max_size=1000000000)