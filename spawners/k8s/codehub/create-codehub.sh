helm upgrae --install --create-namespace -n dohub \
    --set "image.repository=daovieanh99/deepops" \
    --set "image.pullPolicy=Always" \
    --set "image.tag=latest" \
    --set "serviceAccount.enable=false" \
    --set "serviceAccount.automount=false" \
    --set "serviceAccount.name=default" \
    --set "podSecurityContext.fsGroup=100" \
    --set "securityContext.capabilities.add={'SYS_ADMIN'}" \
    --set "securityContext.allowPrivilegeEscalation=true" \
    --set "securityContext.runAsUser=0" \
    --set "service.type=ClusterIP" \
    --set "service.port=8443" \
    --set "ingress.enable=true" \
    --set "ingress.hosts[0].host=daovietanh190499.vkist-hub.com" \
    --set "ingress.hosts[0].paths[0].path=/" \
    --set "ingress.hosts[0].paths[0].pathType=Prefix" \
    --set "ingress.tls[0].secretName=chart-example-tls" \
    --set "ingress.tls[0].hosts[0]=daovietanh190499.vkist-hub.com" \
    --set "mainVolume.claimName=claim-dohub-daovietanh190499" \
    --set "mainVolume.dataPath='/data/nas/dohub/dohub-daovietanh190499'" \
    --set "volumes[0].name=shm-volume" \
    --set "volumes[0].emptyDir.medium=Memory" \
    --set "volumes[1].name=volume-daovietanh190499" \
    --set "volumes[1].persistentVolumeClaim.claimName=claim-dohub-daovietanh190499" \
    --set "volumeMounts[0].mountPath=/dev/shm" \
    --set "volumeMounts[0].name=shm-volume" \
    --set "volumeMounts[1].mountPath=/home/coder" \
    --set "volumeMounts[1].name=volume-daovietanh190499" \
    --set "resources.limits.cpu=1" \
    --set "resources.limits.memory=17179869184" \
    --set "resources.requests.cpu=1" \
    --set "resources.requests.memory=8589934592" \
    dohub-exampleuser spawners/k8s/codehub

# --set "resources.limits.nvidia.com/mig-2g.10gb=1" \
# --set "resources.requests.nvidia.com/mig-2g.10gb=1" \