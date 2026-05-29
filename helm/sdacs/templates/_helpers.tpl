{{/*
공통 레이블
*/}}
{{- define "sdacs.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
셀렉터 레이블
*/}}
{{- define "sdacs.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
전체 이름
*/}}
{{- define "sdacs.fullname" -}}
{{ .Release.Name }}-{{ .Chart.Name }}
{{- end }}
