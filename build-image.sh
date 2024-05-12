docker buildx build \
    --build-arg TARGETOS=linux \
    --build-arg TARGETARCH=amd64 \
	--build-arg KUBE_VERSION=1.30.0 \
	--build-arg HELM_VERSION=3.8.0 \
	-t daovietanh99/dohub:latest .
docker push daovietanh99/dohub:latest