# DeepOpsHubs

[!["GitHub Discussions"](https://img.shields.io/badge/%20GitHub-%20Discussions-gray.svg?longCache=true&logo=github&colorB=purple)](https://github.com/daovietanh190499/DeepOps/discussions) [!["Join us on Slack"](https://img.shields.io/badge/join-us%20on%20slack-gray.svg?longCache=true&logo=slack&colorB=brightgreen)](https://coder.com/community) [![Twitter Follow](https://img.shields.io/twitter/follow/CoderHQ?label=%40CoderHQ&style=social)](https://twitter.com/daovietanh99) [![See latest](https://img.shields.io/static/v1?label=Docs&message=see%20latest&color=blue)](https://github.com/daovietanh190499/DeepOps)

Run [DeepOps Hub](https://github.com/daovietanh190499/DeepOps) on any cluster, system anywhere and
access it in the browser.

![Screenshot](./docs/assets/screenshot-modified.png)

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
