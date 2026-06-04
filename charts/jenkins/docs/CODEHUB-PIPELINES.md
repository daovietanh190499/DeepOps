# Jenkins pipelines — spawn / delete codehub (DirectPV)

Storage: **DirectPV** (`directpv-min-io`, `WaitForFirstConsumer`). No NFS PV/PVC.

| Pipeline | API | Script |
|----------|-----|--------|
| `codehub-spawn` | `POST /start_server/{username}` | `scripts/codehub-spawn.sh` |
| `codehub-delete` | `POST /stop_server/{username}` | `scripts/codehub-delete.sh` |

## Spawn parameters

| Parameter | API / config |
|-----------|----------------|
| `USERNAME` | `user.username` |
| `PASSWORD` | `user.access_password` |
| `CPU`, `RAM`, `GPU` | `ServerOption` |
| `DOCKER_IMAGE`, `IMAGE_TAG` | image |
| `VOLUME_SIZE` | `initServerOptions[].volumeSize` or `storage.defaultWorkspaceSize` |
| `STORAGE_CLASS` | `storage.storageClassName` (default `directpv-min-io`) |
| `NAMESPACE`, `DOMAIN_NAME`, `DEFAULT_PORT` | env |

PVC name: `claim-{NAMESPACE}-{USERNAME}` — provisioned when the codehub pod schedules.

## Delete parameters

| Parameter | API |
|-----------|-----|
| `USERNAME` | `user.username` |
| `NAMESPACE` | env `NAMESPACE` |

`helm uninstall` removes the release; delete orphaned PVC manually if needed:

```bash
kubectl delete pvc claim-dohub-USERNAME -n dohub
```

## CLI example

```bash
export USERNAME=alice PASSWORD=secret CPU=4 RAM=8G VOLUME_SIZE=50Gi
charts/jenkins/scripts/codehub-spawn.sh
```
