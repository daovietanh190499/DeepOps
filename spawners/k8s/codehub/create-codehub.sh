helm upgrade --install --create-namespace -n dohub \
    --set "image.repository=codercom/code-server" \
    --set "image.pullPolicy=IfNotPresent" \
    --set "image.tag=4.89.0-ubuntu" \
    --set "podLabels.dohub-username=exampleuser" \
    --set "secret.name=exampleuser-secret" \
    --set "env.secret.PASSWORD=exampleuser" \
    # --set container.command[0]='/bin/sh -c' \
    # --set container.args[0]='/usr/bin/code-server --bind-addr 0.0.0.0:8443 --disable-telemetry .' \
    --set "serviceAccount.enable=false" \
    --set "serviceAccount.automount=false" \
    --set "serviceAccount.name=default" \
    --set "podSecurityContext.fsGroup=100" \
    --set "securityContext.capabilities.add[0]=SYS_ADMIN" \
    --set "securityContext.allowPrivilegeEscalation=true" \
    --set "securityContext.runAsUser=0" \
    --set "service.type=ClusterIP" \
    --set "service.port=8080" \
    --set "ingress.enabled=true" \
    --set "ingress.className=nginx" \
    --set "ingress.annotations.nginx\.ingress\.kubernetes\.io/proxy-body-size = 0" \
    --set "ingress.annotations.nginx\.ingress\.kubernetes\.io/proxy-read-timeout = 600" \
    --set "ingress.annotations.nginx\.ingress\.kubernetes\.io/proxy-send-timeout = 600" \
    --set "ingress.hosts[0].host=exampleuser.vkist-hub.com" \
    --set "ingress.hosts[0].paths[0].path=/" \
    --set "ingress.hosts[0].paths[0].pathType=Prefix" \
    --set "ingress.tls[0].secretName=tls-dohub-secret" \
    --set "ingress.tls[0].hosts[0]=exampleuser.vkist-hub.com" \
    --set "mainVolume.claimName=claim-dohub-exampleuser" \
    --set "mainVolume.dataPath='/data/nas/dohub/dohub-daovietanh190499'" \
    --set "volumes[0].name=shm-volume" \
    --set "volumes[0].emptyDir.medium=Memory" \
    --set "volumes[1].name=volume-exampleuser" \
    --set "volumes[1].persistentVolumeClaim.claimName=claim-dohub-exampleuser" \
    --set "volumeMounts[0].mountPath=/dev/shm" \
    --set "volumeMounts[0].name=shm-volume" \
    --set "volumeMounts[1].mountPath=/home/coder" \
    --set "volumeMounts[1].name=volume-exampleuser" \
    --set "resources.limits.cpu=1" \
    --set "resources.limits.memory=17179869184" \
    --set "resources.limits.nvidia\.com/gpu=1" \
    --set "resources.requests.cpu=1" \
    --set "resources.requests.memory=8589934592" \
    --set "resources.requests.nvidia\.com/gpu=1" \
    dohub-exampleuser spawners/k8s/codehub