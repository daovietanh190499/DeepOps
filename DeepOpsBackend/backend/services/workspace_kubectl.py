"""kubectl logs/describe/monitor for workspace pods."""

import json
import re
import shlex
import subprocess
from datetime import date, datetime, timedelta, timezone

from backend.models import Workspace

from .gpu_resources import parse_gpu_resources
from .k8s_env import NAMESPACE
from .k8s_status import workspace_pods_for_id

MONITOR_CONTAINER = 'monitor-sidecar'
MONITOR_LOG_DIR = '/tmp/monitor'
MONITOR_LEGACY_LOG_FILE = f'{MONITOR_LOG_DIR}/metrics.jsonl'
MONITOR_DAILY_NAME_RE = re.compile(r'^metrics-(\d{4}-\d{2}-\d{2})\.jsonl$')
MONITOR_DEFAULT_WINDOW_MINUTES = 300
MONITOR_WINDOW_OPTIONS_MINUTES = (5, 15, 30, 60, 300)


def _parse_monitor_window_minutes(raw: str | int | None) -> int:
    try:
        value = int(raw if raw is not None else MONITOR_DEFAULT_WINDOW_MINUTES)
    except (TypeError, ValueError):
        return MONITOR_DEFAULT_WINDOW_MINUTES
    if value in MONITOR_WINDOW_OPTIONS_MINUTES:
        return value
    return MONITOR_DEFAULT_WINDOW_MINUTES


def _monitor_window_label(minutes: int) -> str:
    if minutes < 60:
        return f'{minutes} min'
    hours = minutes // 60
    return '1 hour' if hours == 1 else f'{hours} hours'


def _kubectl(args: list[str], timeout: int = 60) -> tuple[str, str, int]:
    result = subprocess.run(
        ['kubectl', *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    return result.stdout or '', result.stderr or '', result.returncode


def _kubectl_bytes(args: list[str], timeout: int = 120) -> tuple[bytes, str, int]:
    result = subprocess.run(
        ['kubectl', *args],
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    stderr = (result.stderr or b'').decode('utf-8', errors='replace')
    return result.stdout or b'', stderr, result.returncode


def _monitor_daily_date(path: str) -> date | None:
    name = path.rsplit('/', 1)[-1]
    match = MONITOR_DAILY_NAME_RE.match(name)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def _list_monitor_daily_files(pod_name: str) -> tuple[list[str], str]:
    list_cmd = f'ls -1 {shlex.quote(MONITOR_LOG_DIR)}/metrics-*.jsonl 2>/dev/null | sort'
    stdout, stderr, code = _kubectl([
        'exec', pod_name,
        '-n', NAMESPACE,
        '-c', MONITOR_CONTAINER,
        '--', 'sh', '-c', list_cmd,
    ], timeout=30)
    if code != 0 and not stdout.strip():
        return [], (stderr or stdout or '').strip()
    files = []
    for line in stdout.splitlines():
        path = line.strip()
        if not path:
            continue
        if _monitor_daily_date(path) is not None:
            files.append(path)
    return files, ''


def _monitor_files_for_cutoff(all_files: list[str], cutoff: datetime) -> list[str]:
    cutoff_day = cutoff.date()
    selected = [
        path for path in all_files
        if (_monitor_daily_date(path) or date.min) >= cutoff_day
    ]
    return sorted(selected)


def _read_monitor_file_contents(pod_name: str, file_paths: list[str]) -> tuple[str, str, int]:
    if not file_paths:
        return '', '', 0
    cat_cmd = 'cat ' + ' '.join(shlex.quote(path) for path in file_paths)
    return _kubectl([
        'exec', pod_name,
        '-n', NAMESPACE,
        '-c', MONITOR_CONTAINER,
        '--', 'sh', '-c', cat_cmd,
    ], timeout=90)


def _resolve_monitor_pod(
    workspace: Workspace,
    *,
    pod_name: str | None,
) -> tuple[str, list[dict], str]:
    pods = workspace_pods_for_id(str(workspace.id))
    if not pods:
        return '', pods, 'No pods found. The server may be stopped or not deployed yet.'
    selected = pod_name or pods[0]['name']
    if not any(item['name'] == selected for item in pods):
        selected = pods[0]['name']
    return selected, pods, ''


def _pod_container_names(pod_name: str) -> list[str]:
    stdout, _, code = _kubectl([
        'get', 'pod', pod_name,
        '-n', NAMESPACE,
        '-o', 'jsonpath={.spec.containers[*].name}',
    ])
    if code != 0:
        return []
    return [name for name in stdout.split() if name]


def workspace_logs(
    workspace: Workspace,
    *,
    pod_name: str | None = None,
    container: str | None = None,
    tail: int = 500,
) -> dict:
    pods = workspace_pods_for_id(str(workspace.id))
    if not pods:
        return {
            'logs': '',
            'pods': [],
            'selected_pod': '',
            'containers': [],
            'selected_container': container or '',
            'error': 'No pods found. The server may be stopped or not deployed yet.',
        }

    selected = pod_name or pods[0]['name']
    if not any(item['name'] == selected for item in pods):
        selected = pods[0]['name']

    tail_n = max(50, min(int(tail or 500), 5000))
    args = [
        'logs', selected,
        '-n', NAMESPACE,
        f'--tail={tail_n}',
        '--timestamps',
    ]
    if container:
        args.extend(['-c', container])
    else:
        args.extend(['--all-containers=true', '--prefix=true'])

    stdout, stderr, code = _kubectl(args)
    logs = stdout.strip()
    if not logs and stderr:
        logs = stderr.strip()
    if not logs:
        logs = '(no log output)'

    containers = _pod_container_names(selected)
    error = ''
    if code != 0:
        error = stderr.strip() or 'kubectl logs failed'

    return {
        'logs': logs,
        'pods': pods,
        'selected_pod': selected,
        'containers': containers,
        'selected_container': container or '',
        'error': error,
    }


def workspace_describe(
    workspace: Workspace,
    *,
    pod_name: str | None = None,
) -> dict:
    release = workspace.release_name
    pods = workspace_pods_for_id(str(workspace.id))
    sections: list[str] = []

    dep_out, dep_err, dep_code = _kubectl([
        'describe', 'deployment',
        '-n', NAMESPACE,
        '-l', f'app.kubernetes.io/instance={release}',
    ])
    if dep_out.strip():
        sections.append(dep_out.strip())
    elif dep_code != 0 and dep_err.strip():
        sections.append(f'# Deployment\n{dep_err.strip()}')

    target_pods = pods
    if pod_name:
        matched = [item for item in pods if item['name'] == pod_name]
        if matched:
            target_pods = matched

    if not target_pods:
        sections.append('# Pods\nNo pods found for this workspace.')
    else:
        for pod in target_pods:
            pod_out, pod_err, pod_code = _kubectl([
                'describe', 'pod', pod['name'],
                '-n', NAMESPACE,
            ])
            if pod_out.strip():
                sections.append(pod_out.strip())
            elif pod_err.strip():
                sections.append(f'# Pod {pod["name"]}\n{pod_err.strip()}')
            elif pod_code != 0:
                sections.append(f'# Pod {pod["name"]}\n(describe failed)')

    text = '\n\n'.join(sections) if sections else 'Nothing to describe (server not deployed).'
    return {
        'text': text,
        'pods': pods,
        'selected_pod': pod_name or (pods[0]['name'] if pods else ''),
        'release_name': release,
    }


def _parse_metric_ts(raw: str) -> datetime | None:
    text = (raw or '').strip()
    if not text:
        return None
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _pct(used: int | float, limit: int | float) -> float:
    if not limit:
        return 0.0
    return round(min(100.0, max(0.0, (float(used) / float(limit)) * 100.0)), 2)


def workspace_monitor_metrics(
    workspace: Workspace,
    *,
    pod_name: str | None = None,
    window_minutes: int | None = None,
) -> dict:
    window_minutes = _parse_monitor_window_minutes(window_minutes)
    window_options = [
        {'minutes': m, 'label': _monitor_window_label(m)}
        for m in MONITOR_WINDOW_OPTIONS_MINUTES
    ]
    selected, pods, pod_error = _resolve_monitor_pod(workspace, pod_name=pod_name)
    gpu_spec = parse_gpu_resources(workspace.gpu)
    if pod_error:
        return {
            'points': [],
            'pods': pods,
            'selected_pod': '',
            'has_gpu': gpu_spec['enabled'],
            'window_minutes': window_minutes,
            'window_label': _monitor_window_label(window_minutes),
            'window_options': window_options,
            'log_days': [],
            'error': pod_error,
        }

    daily_files, list_error = _list_monitor_daily_files(selected)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    file_paths = _monitor_files_for_cutoff(daily_files, cutoff)

    stdout = ''
    error = list_error
    if file_paths:
        stdout, read_err, code = _read_monitor_file_contents(selected, file_paths)
        if code != 0:
            error = read_err or 'Failed to read monitor metrics from sidecar.'
    elif not error:
        stdout, read_err, code = _read_monitor_file_contents(selected, [MONITOR_LEGACY_LOG_FILE])
        if code != 0:
            error = read_err or 'Failed to read monitor metrics from sidecar.'
        elif not stdout.strip():
            error = 'No monitor metrics files found yet.'

    if error:
        return {
            'points': [],
            'pods': pods,
            'selected_pod': selected,
            'has_gpu': gpu_spec['enabled'],
            'window_minutes': window_minutes,
            'window_label': _monitor_window_label(window_minutes),
            'window_options': window_options,
            'log_days': [_monitor_daily_date(path).isoformat() for path in file_paths if _monitor_daily_date(path)],
            'error': error,
        }

    points: list[dict] = []
    saw_gpu = False

    for line in (stdout or '').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue

        ts = _parse_metric_ts(str(row.get('ts', '')))
        if ts is None or ts < cutoff:
            continue

        cpu_limit = int(row.get('cpu_limit_millicores') or 0)
        mem_limit = int(row.get('memory_limit_bytes') or 0)
        cpu_used = int(row.get('cpu_millicores') or 0)
        mem_used = int(row.get('memory_bytes') or 0)

        gpu_util = row.get('gpu_util_pct')
        gpu_mem_used = row.get('gpu_mem_used_mib')
        gpu_mem_total = row.get('gpu_mem_total_mib')

        gpu_util_pct = None
        gpu_mem_pct = None
        if gpu_util is not None and gpu_util != 'null':
            try:
                gpu_util_pct = float(gpu_util)
                saw_gpu = True
            except (TypeError, ValueError):
                gpu_util_pct = None
        if gpu_mem_used is not None and gpu_mem_total is not None and gpu_mem_used != 'null':
            try:
                used_mib = float(gpu_mem_used)
                total_mib = float(gpu_mem_total)
                if total_mib > 0:
                    gpu_mem_pct = _pct(used_mib, total_mib)
                    saw_gpu = True
            except (TypeError, ValueError):
                gpu_mem_pct = None

        points.append({
            'ts': ts.isoformat().replace('+00:00', 'Z'),
            'cpu_pct': _pct(cpu_used, cpu_limit),
            'memory_pct': _pct(mem_used, mem_limit),
            'gpu_util_pct': gpu_util_pct,
            'gpu_mem_pct': gpu_mem_pct,
        })

    return {
        'points': points,
        'pods': pods,
        'selected_pod': selected,
        'has_gpu': gpu_spec['enabled'] and saw_gpu,
        'window_minutes': window_minutes,
        'window_label': _monitor_window_label(window_minutes),
        'window_options': window_options,
        'log_days': [
            day.isoformat()
            for path in file_paths
            if (day := _monitor_daily_date(path)) is not None
        ],
        'error': error,
    }


def workspace_monitor_file(
    workspace: Workspace,
    *,
    pod_name: str | None = None,
) -> dict:
    """Archive daily metrics JSONL files from the monitor sidecar for download."""
    selected, pods, pod_error = _resolve_monitor_pod(workspace, pod_name=pod_name)
    if pod_error:
        return {
            'content': b'',
            'filename': '',
            'selected_pod': '',
            'content_type': 'application/gzip',
            'error': pod_error,
        }

    tar_cmd = (
        f'cd {shlex.quote(MONITOR_LOG_DIR)} && '
        'if ls metrics-*.jsonl >/dev/null 2>&1; then tar czf - metrics-*.jsonl; fi'
    )
    content, stderr, code = _kubectl_bytes([
        'exec', selected,
        '-n', NAMESPACE,
        '-c', MONITOR_CONTAINER,
        '--', 'sh', '-c', tar_cmd,
    ], timeout=120)

    if code != 0 or not content:
        legacy_cmd = f'cat {shlex.quote(MONITOR_LEGACY_LOG_FILE)}'
        legacy_out, legacy_err, legacy_code = _kubectl([
            'exec', selected,
            '-n', NAMESPACE,
            '-c', MONITOR_CONTAINER,
            '--', 'sh', '-c', legacy_cmd,
        ], timeout=60)
        if legacy_code == 0 and legacy_out.strip():
            slug = (workspace.slug or 'workspace').replace('/', '-')
            return {
                'content': legacy_out.encode('utf-8'),
                'filename': f'dohub-{slug}-metrics.jsonl',
                'selected_pod': selected,
                'content_type': 'application/x-ndjson',
                'error': '',
            }
        err = (stderr or legacy_err or '').strip() or 'Failed to read monitor metrics files from sidecar.'
        return {
            'content': b'',
            'filename': '',
            'selected_pod': selected,
            'content_type': 'application/gzip',
            'error': err,
        }

    slug = (workspace.slug or 'workspace').replace('/', '-')
    return {
        'content': content,
        'filename': f'dohub-{slug}-metrics.tar.gz',
        'selected_pod': selected,
        'content_type': 'application/gzip',
        'error': '',
    }
