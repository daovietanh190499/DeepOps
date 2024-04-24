helm install \
    --set global.imageRegistry="daovietanh99" \
    --set global.caCrt= ""\
    --set global.caKey= ""\
    --set dohub.replicas=1 \
    --set dohub.image="dohub" \
    --set dohub.githubClientId="abc" \
    --set dohub.githubClientSecret="def" \
    --set dohub.adminUsers="daovietanh190499" \
    --set dohub.defaultPort=8443 \
    --set dohub.defaultSpawner="k8s" \
    vkist dohub-helm-chart/