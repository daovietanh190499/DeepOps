{{/*
Expand the name of the chart.
*/}}
{{- define "codehub.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "codehub.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "codehub.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "codehub.labels" -}}
helm.sh/chart: {{ include "codehub.chart" . }}
{{ include "codehub.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "codehub.selectorLabels" -}}
app.kubernetes.io/name: {{ include "codehub.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "codehub.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "codehub.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "codehub.sidecarServiceAccountName" -}}
{{- default (printf "%s-sidecar" (include "codehub.fullname" .)) .Values.sidecar.serviceAccount.name }}
{{- end }}

{{/*
Legacy alias for ssh-bridge RBAC templates.
*/}}
{{- define "codehub.sshBridgeServiceAccountName" -}}
{{- include "codehub.sidecarServiceAccountName" . }}
{{- end }}

{{/*
Ingress controller mode: auto | nginx | traefik | both
- auto: Traefik when traefik.io Middleware CRD exists, else nginx
- both: Traefik path + middleware when CRD exists, else nginx regex + rewrite
*/}}
{{- define "codehub.ingressController" -}}
{{- $c := default "auto" .Values.ingress.controller -}}
{{- if eq $c "auto" -}}
{{- if (.Capabilities.APIVersions.Has "traefik.io/v1alpha1/Middleware") -}}
traefik
{{- else -}}
nginx
{{- end -}}
{{- else -}}
{{- $c -}}
{{- end -}}
{{- end -}}

{{- define "codehub.ingressUsesNginx" -}}
{{- $c := include "codehub.ingressController" . -}}
{{- if or (eq $c "nginx") (eq $c "both") -}}true{{- end -}}
{{- end -}}

{{- define "codehub.ingressUsesTraefik" -}}
{{- $c := include "codehub.ingressController" . -}}
{{- if or (eq $c "traefik") (eq $c "both") -}}true{{- end -}}
{{- end -}}

{{- define "codehub.traefikMiddlewareSupported" -}}
{{- if (.Capabilities.APIVersions.Has "traefik.io/v1alpha1/Middleware") -}}true{{- end -}}
{{- end -}}

{{/*
Nginx regex path + rewrite (not used when Traefik middleware handles stripPrefix).
*/}}
{{- define "codehub.sidecarIngressUsesNginxPath" -}}
{{- $c := include "codehub.ingressController" . -}}
{{- if eq $c "nginx" -}}true
{{- else if and (eq $c "both") (ne (include "codehub.traefikMiddlewareSupported" .) "true") -}}true
{{- end -}}
{{- end -}}

{{/*
Public hub path -> strip prefix before inner wstunnel path (e.g. /user/slug).
*/}}
{{- define "codehub.sidecarStripPrefix" -}}
{{- $publicPath := .publicPath -}}
{{- $innerPrefix := .innerPrefix -}}
{{- trimSuffix (printf "/%s" $innerPrefix) $publicPath -}}
{{- end -}}

{{/*
Sidecar ingress path rule (nginx uses regex + rewrite; traefik uses Prefix + middleware).
*/}}
{{- define "codehub.sidecarIngressPath" -}}
{{- $publicPath := .publicPath -}}
{{- $innerPrefix := .innerPrefix -}}
{{- $stripPrefix := include "codehub.sidecarStripPrefix" . -}}
{{- $root := .root -}}
{{- if and $stripPrefix (eq (include "codehub.sidecarIngressUsesNginxPath" $root) "true") -}}
path: {{ $publicPath }}(/|$)(.*)
pathType: ImplementationSpecific
{{- else -}}
path: {{ $publicPath }}
pathType: Prefix
{{- end -}}
{{- end -}}

{{/*
Annotations for sidecar ingress (websocket + path rewrite).
*/}}
{{- define "codehub.sidecarIngressAnnotations" -}}
{{- $root := .root -}}
{{- $fullName := .fullName -}}
{{- $innerPrefix := .innerPrefix -}}
{{- $stripPrefix := .stripPrefix -}}
{{- $middlewareName := .middlewareName -}}
{{- if eq (include "codehub.sidecarIngressUsesNginxPath" $root) "true" }}
{{- if $stripPrefix }}
nginx.ingress.kubernetes.io/use-regex: "true"
nginx.ingress.kubernetes.io/rewrite-target: /{{ $innerPrefix }}/$2
{{- end }}
{{- end }}
{{- if eq (include "codehub.ingressController" $root) "nginx" }}
nginx.ingress.kubernetes.io/websocket-services: {{ $fullName | quote }}
nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
nginx.ingress.kubernetes.io/proxy-send-timeout: "600"
nginx.ingress.kubernetes.io/proxy-buffering: "off"
nginx.ingress.kubernetes.io/proxy-http-version: "1.1"
{{- end }}
{{- if and (eq (include "codehub.ingressUsesTraefik" $root) "true") (eq (include "codehub.traefikMiddlewareSupported" $root) "true") }}
{{- if and $stripPrefix $middlewareName }}
traefik.ingress.kubernetes.io/router.middlewares: {{ $root.Release.Namespace }}-{{ $middlewareName }}@kubernetescrd
{{- end }}
traefik.ingress.kubernetes.io/router.priority: {{ $root.Values.sidecarIngress.priority | default "1000" | quote }}
{{- end }}
{{- end -}}
