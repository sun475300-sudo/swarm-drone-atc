{{/*
_helpers.tpl — SDACS Helm 차트 공통 헬퍼 함수 모음
템플릿 전체에서 재사용되는 이름, 레이블, 셀렉터 등을 정의
*/}}

{{/*
차트 전체 이름 (63자 이하로 잘림 — DNS 서브도메인 제한)
Release.Name이 차트 이름을 이미 포함하고 있으면 중복 방지
*/}}
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

{{/*
차트 단독 이름 (63자 이하)
*/}}
{{- define "sdacs.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
차트 버전 레이블 (app.kubernetes.io/version)
특수문자를 +로 치환하여 레이블 호환성 확보
*/}}
{{- define "sdacs.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
공통 레이블 — 모든 리소스에 붙는 표준 Kubernetes 레이블 세트
app.kubernetes.io/* 권장 레이블 규격 준수
*/}}
{{- define "sdacs.labels" -}}
helm.sh/chart: {{ include "sdacs.chart" . }}
{{ include "sdacs.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
셀렉터 레이블 — Deployment/Service 매칭에 사용 (변경 불가)
이 레이블이 바뀌면 기존 Deployment를 삭제 후 재생성해야 함
*/}}
{{- define "sdacs.selectorLabels" -}}
app.kubernetes.io/name: {{ include "sdacs.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Redis 리소스 이름
*/}}
{{- define "sdacs.redis.fullname" -}}
{{- printf "%s-redis" (include "sdacs.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
PostgreSQL 리소스 이름
*/}}
{{- define "sdacs.postgresql.fullname" -}}
{{- printf "%s-postgresql" (include "sdacs.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Redis 접속 URL — 환경변수로 백엔드에 주입
*/}}
{{- define "sdacs.redis.url" -}}
{{- printf "redis://%s:%d" (include "sdacs.redis.fullname" .) (.Values.redis.port | int) }}
{{- end }}

{{/*
PostgreSQL 접속 URL — 환경변수로 백엔드에 주입
*/}}
{{- define "sdacs.postgresql.url" -}}
{{- printf "postgresql://sdacs:$(POSTGRES_PASSWORD)@%s:%d/%s" (include "sdacs.postgresql.fullname" .) (.Values.postgresql.port | int) .Values.postgresql.database }}
{{- end }}

{{/*
서비스 계정 이름 결정 로직
values.yaml의 serviceAccount.name이 설정되어 있으면 그것을 사용,
아니면 fullname 헬퍼로 자동 생성
*/}}
{{- define "sdacs.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "sdacs.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
