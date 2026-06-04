{{/*
Expand the name of the chart.
*/}}
{{- define "jenkins.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a fully qualified app name.
*/}}
{{- define "jenkins.fullname" -}}
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

{{- define "jenkins.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "jenkins.labels" -}}
helm.sh/chart: {{ include "jenkins.chart" . }}
{{ include "jenkins.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "jenkins.selectorLabels" -}}
app.kubernetes.io/name: {{ include "jenkins.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "jenkins.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "jenkins.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "jenkins.namespace" -}}
{{- default .Release.Namespace .Values.kubernetesAgent.namespace }}
{{- end }}

{{- define "jenkins.adminUser" -}}
{{- if .Values.controller.existingSecret }}
{{- .Values.controller.adminUser }}
{{- else }}
{{- .Values.controller.adminUser }}
{{- end }}
{{- end }}

{{- define "jenkins.adminPassword" -}}
{{- if .Values.controller.adminPassword }}
{{- .Values.controller.adminPassword }}
{{- else }}
{{- $secretName := printf "%s-admin" (include "jenkins.fullname" .) }}
{{- $secret := lookup "v1" "Secret" .Release.Namespace $secretName }}
{{- if and $secret (index $secret.data "jenkins-admin-password") }}
{{- index $secret.data "jenkins-admin-password" | b64dec }}
{{- else }}
{{- randAlphaNum 24 }}
{{- end }}
{{- end }}
{{- end }}

{{- define "jenkins.jenkinsUrl" -}}
{{- if .Values.configurationAsCode.jenkinsUrl }}
{{- .Values.configurationAsCode.jenkinsUrl }}
{{- else if .Values.kubernetesAgent.jenkinsUrl }}
{{- .Values.kubernetesAgent.jenkinsUrl }}
{{- else if .Values.ingress.enabled }}
{{- $host := (index .Values.ingress.hosts 0).host }}
{{- if .Values.ingress.tls }}
{{- printf "https://%s" $host }}
{{- else }}
{{- printf "http://%s" $host }}
{{- end }}
{{- else }}
{{- printf "http://%s.%s.svc.cluster.local:%v" (include "jenkins.fullname" .) .Release.Namespace .Values.service.httpPort }}
{{- end }}
{{- end }}

{{- define "jenkins.jenkinsTunnel" -}}
{{- if .Values.kubernetesAgent.jenkinsTunnel }}
{{- .Values.kubernetesAgent.jenkinsTunnel }}
{{- else }}
{{- printf "%s.%s.svc.cluster.local:%v" (include "jenkins.fullname" .) .Release.Namespace .Values.service.agentListenerPort }}
{{- end }}
{{- end }}

{{- define "jenkins.pluginsTxt" -}}
{{- range .Values.plugins -}}
{{ if kindIs "string" . }}{{ . }}{{ else }}{{ .name }}{{ if .version }}:{{ .version }}{{ end }}{{ end }}
{{ end -}}
{{- end }}
