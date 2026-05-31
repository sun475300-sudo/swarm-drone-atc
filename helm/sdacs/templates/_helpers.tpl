{{/*
공통 헬퍼 템플릿 (P715 — Docker Compose → Kubernetes Helm 변환)
*/}}

{{/* 차트 이름 */}}
{{- define "sdacs.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* 전체 릴리스 이름 */}}
{{- define "sdacs.fullname" -}}
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

{{/* 차트 레이블 */}}
{{- define "sdacs.labels" -}}
helm.sh/chart: {{ include "sdacs.chart" . }}
{{ include "sdacs.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/* 셀렉터 레이블 */}}
{{- define "sdacs.selectorLabels" -}}
app.kubernetes.io/name: {{ include "sdacs.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/* 차트 버전 레이블 */}}
{{- define "sdacs.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}
