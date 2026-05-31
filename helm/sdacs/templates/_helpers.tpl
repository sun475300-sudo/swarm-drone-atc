{{- define "sdacs.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "sdacs.fullname" -}}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "sdacs.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "sdacs.labels" -}}
helm.sh/chart: {{ include "sdacs.chart" . }}
{{ include "sdacs.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "sdacs.selectorLabels" -}}
app.kubernetes.io/name: {{ include "sdacs.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
