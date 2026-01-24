{{/*
ONE-DATA-STUDIO Helm Chart Helper Templates
*/}}

{{/*
Expand the name of the chart.
*/}}
{{- define "one-data.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "one-data.fullname" -}}
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
Common labels
*/}}
{{- define "one-data.labels" -}}
helm.sh/chart: {{ include "one-data.chart" . }}
{{ include "one-data.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "one-data.selectorLabels" -}}
app.kubernetes.io/name: {{ include "one-data.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "one-data.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
=============================================================================
CREDENTIAL VALIDATION HELPERS
These helpers ensure that required credentials are set before deployment.
Production deployments will fail if credentials are empty or use defaults.
=============================================================================
*/}}

{{/*
Check if running in production environment
*/}}
{{- define "one-data.isProduction" -}}
{{- if or (eq .Values.global.environment "production") (eq .Values.global.environment "prod") -}}
true
{{- end -}}
{{- end }}

{{/*
Validate MinIO credentials
REQUIRED: minio.credentials.rootUser and minio.credentials.rootPassword
*/}}
{{- define "one-data.validateMinioCredentials" -}}
{{- if .Values.infrastructure.minio.enabled }}
{{- if not .Values.infrastructure.minio.credentials.rootUser }}
{{- fail "ERROR: infrastructure.minio.credentials.rootUser is required. Set via --set or values override." }}
{{- end }}
{{- if not .Values.infrastructure.minio.credentials.rootPassword }}
{{- fail "ERROR: infrastructure.minio.credentials.rootPassword is required. Set via --set or values override." }}
{{- end }}
{{- if and (eq .Values.infrastructure.minio.credentials.rootUser "admin") (include "one-data.isProduction" .) }}
{{- fail "ERROR: Default MinIO username 'admin' is not allowed in production. Use a unique username." }}
{{- end }}
{{- if and (lt (len .Values.infrastructure.minio.credentials.rootPassword) 8) (include "one-data.isProduction" .) }}
{{- fail "ERROR: MinIO password must be at least 8 characters in production." }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Validate MySQL credentials
REQUIRED: mysql.database.password
*/}}
{{- define "one-data.validateMysqlCredentials" -}}
{{- if .Values.infrastructure.mysql.enabled }}
{{- if not .Values.infrastructure.mysql.database.password }}
{{- fail "ERROR: infrastructure.mysql.database.password is required. Set via --set or values override." }}
{{- end }}
{{- if and (lt (len .Values.infrastructure.mysql.database.password) 8) (include "one-data.isProduction" .) }}
{{- fail "ERROR: MySQL password must be at least 8 characters in production." }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Validate Redis credentials
REQUIRED: redis.password
*/}}
{{- define "one-data.validateRedisCredentials" -}}
{{- if .Values.infrastructure.redis.enabled }}
{{- if not .Values.infrastructure.redis.password }}
{{- fail "ERROR: infrastructure.redis.password is required. Set via --set or values override." }}
{{- end }}
{{- if and (lt (len .Values.infrastructure.redis.password) 8) (include "one-data.isProduction" .) }}
{{- fail "ERROR: Redis password must be at least 8 characters in production." }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Validate Grafana credentials (if monitoring enabled)
REQUIRED: grafana.adminPassword when monitoring.grafana.enabled
*/}}
{{- define "one-data.validateGrafanaCredentials" -}}
{{- if and .Values.monitoring.enabled .Values.monitoring.grafana.enabled }}
{{- if not .Values.monitoring.grafana.adminPassword }}
{{- fail "ERROR: monitoring.grafana.adminPassword is required when Grafana is enabled. Set via --set or values override." }}
{{- end }}
{{- if and (lt (len .Values.monitoring.grafana.adminPassword) 8) (include "one-data.isProduction" .) }}
{{- fail "ERROR: Grafana admin password must be at least 8 characters in production." }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Validate JWT secret key
REQUIRED: services.jwtSecretKey for all service authentication
*/}}
{{- define "one-data.validateJwtSecret" -}}
{{- if not .Values.services.jwtSecretKey }}
{{- fail "ERROR: services.jwtSecretKey is required. Set via --set or values override. Generate with: openssl rand -base64 32" }}
{{- end }}
{{- if and (lt (len .Values.services.jwtSecretKey) 32) (include "one-data.isProduction" .) }}
{{- fail "ERROR: JWT secret key must be at least 32 characters in production. Generate with: openssl rand -base64 32" }}
{{- end }}
{{- end }}

{{/*
Validate TLS configuration in production
Warns if TLS is not enabled for ingress in production environment
*/}}
{{- define "one-data.validateTLS" -}}
{{- if include "one-data.isProduction" . }}
{{- if and .Values.alldata.ingress.enabled (not .Values.alldata.ingress.tls) }}
{{- fail "ERROR: TLS must be enabled for Alldata ingress in production. Set alldata.ingress.tls=true and configure cert-manager." }}
{{- end }}
{{- if and .Values.bisheng.ingress.enabled (not .Values.bisheng.ingress.tls) }}
{{- fail "ERROR: TLS must be enabled for Bisheng ingress in production. Set bisheng.ingress.tls=true and configure cert-manager." }}
{{- end }}
{{- if and .Values.cube.modelServing.ingress.enabled (not .Values.cube.modelServing.ingress.tls) }}
{{- fail "ERROR: TLS must be enabled for Cube ingress in production. Set cube.modelServing.ingress.tls=true and configure cert-manager." }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Master validation function - call this to validate all required credentials
This should be called from the main templates to ensure all validations run
*/}}
{{- define "one-data.validateAllCredentials" -}}
{{- include "one-data.validateMinioCredentials" . }}
{{- include "one-data.validateMysqlCredentials" . }}
{{- include "one-data.validateRedisCredentials" . }}
{{- include "one-data.validateGrafanaCredentials" . }}
{{- include "one-data.validateJwtSecret" . }}
{{- include "one-data.validateTLS" . }}
{{- end }}

{{/*
Generate a secure random password if not provided (for development only)
DO NOT use this in production - always provide explicit passwords
*/}}
{{- define "one-data.generatePassword" -}}
{{- if include "one-data.isProduction" . }}
{{- fail "Cannot auto-generate passwords in production. Provide explicit credentials." }}
{{- else }}
{{- randAlphaNum 16 }}
{{- end }}
{{- end }}
