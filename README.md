# DeepOps

```shell
cd spawners/k8s/dohub_k8s/
```

```shell
kubectl apply -f dohub-service-account.yaml
```

```shell
kubectl apply -f dohub-cluster-role.yaml
```

```shell
kubectl apply -f dohub-cluster-role-binding.yaml
```

```shell
kubectl apply -f dohub-config-map.yaml
```

```shell
kubectl apply -f dohub-pv.yaml
```

```shell
kubectl apply -f dohub-pvc.yaml
```

```shell
kubectl apply -f dohub-pv-server.yaml
```

```shell
kubectl apply -f dohub-pvc-server.yaml
```

```shell
kubectl apply -f dohub-service-without-nginx.yaml
```

```shell
kubectl apply -f dohub-without-nginx.yaml
```
