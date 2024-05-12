docker buildx build \
    --build-arg TARGETOS=linux \
    --build-arg TARGETARCH=amd64 \
	--build-arg KUBE_VERSION=v1.30.0 \
	--build-arg HELM_VERSION=v3.8.0 \
	-t daovietanh99/dohub:latest .
docker push daovietanh99/dohub:latest
docker image rm daovietanh99/dohub:latest