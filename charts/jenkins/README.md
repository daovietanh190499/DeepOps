# Jenkins Helm Chart (DeepOps)

Chart cài **Jenkins LTS đầy đủ** trên Kubernetes:

- Controller `jenkins/jenkins:lts-jdk17` + PVC `JENKINS_HOME`
- Cài **plugin** tự động lần đầu (Kubernetes, Blue Ocean, Pipeline, Git, JCasC, …)
- **Configuration as Code** (admin, security, Kubernetes cloud)
- **Dynamic agents** trên K8s (RBAC + ServiceAccount)
- Service HTTP `8080` + JNLP `50000`
- Ingress (tuỳ chọn TLS)

## Cài đặt nhanh

```bash
# Đặt mật khẩu admin cố định (khuyến nghị)
helm upgrade --install jenkins ./charts/jenkins \
  --create-namespace -n jenkins \
  --set controller.adminPassword='YourStrongPassword' \
  --set ingress.hosts[0].host=jenkins.your-domain.com \
  --set configurationAsCode.jenkinsUrl=https://jenkins.your-domain.com
```

Hoặc dùng file values riêng:

```bash
cp charts/jenkins/values-production.yaml.example charts/jenkins/values-production.yaml
# chỉnh file rồi:
helm upgrade --install jenkins ./charts/jenkins -n jenkins -f charts/jenkins/values-production.yaml
```

## Lấy mật khẩu admin

```bash
kubectl get secret jenkins-admin -n jenkins \
  -o jsonpath='{.data.jenkins-admin-password}' | base64 -d; echo
# User mặc định: admin
```

## Kiểm tra chart

```bash
helm lint ./charts/jenkins
helm template jenkins ./charts/jenkins --debug
```

## Tuỳ chỉnh chính

| Values | Mô tả |
|--------|--------|
| `controller.adminPassword` | Mật khẩu admin (nên set rõ) |
| `persistence.size` | Dung lượng PVC |
| `plugins` | Danh sách plugin (`plugins.txt`) |
| `ingress.hosts` | Host truy cập UI |
| `kubernetesAgent.enabled` | Bật agent động trên K8s |
| `configurationAsCode.jenkinsUrl` | URL public (cho webhook / K8s cloud) |

## Pipelines codehub (spawn / delete)

Tương đương API `POST /start_server/{username}` và `POST /stop_server/{username}`:

- `pipelines/codehub-spawn.Jenkinsfile`
- `pipelines/codehub-delete.Jenkinsfile`
- `scripts/codehub-spawn.sh` / `scripts/codehub-delete.sh`

Chi tiết tham số: [docs/CODEHUB-PIPELINES.md](./docs/CODEHUB-PIPELINES.md)

## Gỡ cài đặt

```bash
helm uninstall jenkins -n jenkins
# PVC không tự xóa nếu cần giữ dữ liệu
```
