helm upgrade -i --create-namespace -n dohub vkist spawners/k8s/dohub --reset-values --values spawners/k8s/dohub/values.yaml
kubectl rollout restart deploy -n dohub
kubectl delete replicaset $(kubectl get replicaset -n dohub -o jsonpath='{.items[?(@.spec.replicas==0)].metadata.name }') -n dohub