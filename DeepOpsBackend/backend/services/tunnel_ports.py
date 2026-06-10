"""WebSocket tunnel port exposure (wstunnel) for workspace main container."""

PORT_TUNNEL_PATH_PREFIX = 'port-tunnel'
MAX_TUNNEL_PORTS = 32


def parse_tunnel_ports(raw) -> list[int]:
    """Parse port list from JSON array, comma-separated string, or list of ints."""
    if raw is None:
        return []
    items: list = []
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        if text.startswith('['):
            import json
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError('ports must be valid JSON array') from exc
            if not isinstance(parsed, list):
                raise ValueError('ports must be a JSON array')
            items = parsed
        else:
            items = [part.strip() for part in text.replace(';', ',').split(',') if part.strip()]
    elif isinstance(raw, list):
        items = raw
    else:
        raise ValueError('ports must be a list or comma-separated string')

    ports: list[int] = []
    seen: set[int] = set()
    for item in items:
        try:
            port = int(item)
        except (TypeError, ValueError) as exc:
            raise ValueError(f'invalid port: {item!r}') from exc
        if port < 1 or port > 65535:
            raise ValueError(f'port out of range: {port}')
        if port in seen:
            continue
        seen.add(port)
        ports.append(port)

    if len(ports) > MAX_TUNNEL_PORTS:
        raise ValueError(f'at most {MAX_TUNNEL_PORTS} ports allowed')
    return sorted(ports)


def port_tunnel_wss_url(workspace) -> str:
    return f'wss://{workspace.hostname}/{PORT_TUNNEL_PATH_PREFIX}'


def wstunnel_client_local_flag(local_port: int, remote_port: int, target_host: str = '127.0.0.1') -> str:
    return f'tcp://{local_port}:{target_host}:{remote_port}'


def wstunnel_client_command(
    workspace,
    ports: list[int],
    *,
    local_ports: dict[int, int] | None = None,
) -> str:
    """Single wstunnel client command forwarding all ports (local == remote by default)."""
    if not ports:
        return ''
    local_ports = local_ports or {}
    flags = [
        wstunnel_client_local_flag(local_ports.get(p, p), p)
        for p in ports
    ]
    local_part = ' '.join(f'-L {flag}' for flag in flags)
    return (
        f'wstunnel client --log-lvl=warn -P {PORT_TUNNEL_PATH_PREFIX} '
        f'{local_part} {port_tunnel_wss_url(workspace)}'
    )


def tunnel_port_entries(workspace, ports: list[int]) -> list[dict]:
    entries = []
    for port in ports:
        local = port
        entries.append({
            'port': port,
            'local_port': local,
            'remote_host': '127.0.0.1',
            'command': (
                f'wstunnel client --log-lvl=warn -P {PORT_TUNNEL_PATH_PREFIX} '
                f'-L tcp://{local}:127.0.0.1:{port} {port_tunnel_wss_url(workspace)}'
            ),
        })
    return entries


def tunnel_info_payload(workspace) -> dict:
    ports = parse_tunnel_ports(workspace.ws_tunnel_ports)
    combined = wstunnel_client_command(workspace, ports)
    return {
        'enabled': bool(ports),
        'ports': ports,
        'ports_text': ', '.join(str(p) for p in ports),
        'wss_url': port_tunnel_wss_url(workspace),
        'path_prefix': PORT_TUNNEL_PATH_PREFIX,
        'client_command': combined,
        'port_commands': tunnel_port_entries(workspace, ports),
        'curl_example': (
            f'curl http://localhost:{ports[0]}/'
            if ports else ''
        ),
    }
