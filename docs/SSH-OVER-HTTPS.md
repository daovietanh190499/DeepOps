# SSH over HTTPS (Dohub workspaces)

Connect to a codehub pod with normal `ssh` through **HTTPS port 443**, for networks that block SSH port 22.

## Architecture

```
ssh client
  → ProxyCommand: wstunnel client -L stdio://127.0.0.1:2222 wss://HOST/ssh-tunnel
  → nginx ingress (TLS, WebSocket)
  → wstunnel server (sidecar, path prefix ssh-tunnel)
  → asyncssh on 127.0.0.1:2222 (key auth, no OpenSSH in main container)
  → bash shell
```

Uses [wstunnel](https://github.com/erebe/wstunnel) for the WebSocket tunnel and [asyncssh](https://github.com/ronf/asyncssh) for the in-pod SSH server.

## 1. Generate keys in the UI

1. Open **My servers** → click a server card.
2. Use **Generate SSH key pair**.
3. Download the private key and save as `~/.ssh/dohub-<slug>` (`chmod 600`).
4. Start the server if it is offline.

## 2. Install wstunnel (client)

Download a release binary from [wstunnel releases](https://github.com/erebe/wstunnel/releases) and put `wstunnel` on your `PATH`.

## 3. ~/.ssh/config

```sshconfig
Host dohub-myworkspace
    HostName myworkspace-youruser.dohub.com
    User coder
    IdentityFile ~/.ssh/dohub-myworkspace
    ProxyCommand wstunnel client --log-lvl=warn -P ssh-tunnel -L stdio://127.0.0.1:2222 wss://%h/ssh-tunnel
    StrictHostKeyChecking accept-new
```

Connect:

```bash
ssh dohub-myworkspace
```

One-liner without config file:

```bash
ssh -i ~/.ssh/dohub-myworkspace -o ProxyCommand="wstunnel client --log-lvl=warn -P ssh-tunnel -L stdio://127.0.0.1:2222 wss://%h/ssh-tunnel" coder@myworkspace-youruser.dohub.com
```

## 4. Build & deploy

```bash
docker build -t dohub/ssh-bridge:latest charts/codehub/ssh-bridge
./build-and-deploy.sh -t latest all
python3 manage.py migrate   # inside hub pod or locally
```

Optional:

```bash
export SSH_BRIDGE_IMAGE=dohub/ssh-bridge
export SSH_BRIDGE_TAG=latest
```

## 5. Sidecar processes

| Process | Role |
|---------|------|
| `python server.py` | asyncssh on `127.0.0.1:2222` |
| `wstunnel server` | WebSocket on `:8022`, forwards only to `127.0.0.1:2222` |

Ingress path `/ssh-tunnel` must match wstunnel path prefix `ssh-tunnel` (`-P` client / `-r` server).

## 6. API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/workspaces/<id>/ssh` | WSS URL, wstunnel ProxyCommand, config snippet |
| POST | `/workspaces/<id>/ssh/generate` | Create/rotate keys, sync to cluster |
| GET | `/workspaces/<id>/ssh/download` | Download stored private key |

## Troubleshooting

- **`logout` then SSH hangs:** Rebuild and redeploy `ssh-bridge` (log build id: `ssh-bridge-2026-06-08-logout-detect`). Restart the workspace pod. Sidecar logs should show `remote shell exit detected` then `SSH session closing` when you type `exit`.
- **`command terminated with exit code 130`:** Usually from **Ctrl+C** (`130` = SIGINT). `kubectl exec` prints this on stderr when the session is interrupted. Type `exit` without Ctrl+C for a clean disconnect.

## Security

- Public-key auth only (no passwords).
- wstunnel server uses `--restrict-to 127.0.0.1:2222` so tunnels cannot reach other pod addresses.
- Private keys encrypted at rest in the hub database.
