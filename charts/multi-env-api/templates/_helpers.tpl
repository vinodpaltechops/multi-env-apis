{{- define "app.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "app.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "app.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{ include "app.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/environment: {{ .Values.environment | quote }}
{{- end -}}

{{- define "app.selectorLabels" -}}
app.kubernetes.io/name: {{ include "app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "app.image" -}}
{{- printf "%s@%s" (required "image.repository is required" .Values.image.repository) (required "image.digest is required (sha256:...)" .Values.image.digest) -}}
{{- end -}}

{{- define "app.hasSecrets" -}}
{{- if .Values.keyVault.objects -}}true{{- end -}}
{{- end -}}

{{/* Env shared by the app container and the migration Job */}}
{{- define "app.env" -}}
- {name: ENVIRONMENT, value: {{ .Values.environment | quote }}}
- {name: DB_SERVER, value: {{ .Values.app.db.server | quote }}}
- {name: DB_NAME, value: {{ .Values.app.db.name | quote }}}
- {name: DB_AUTH, value: {{ .Values.app.db.auth | quote }}}
- {name: SECRETS_DIR, value: {{ .Values.keyVault.mountPath | quote }}}
- {name: TMPDIR, value: /tmp}
{{- range $k, $v := .Values.app.extraEnv }}
- {name: {{ $k | quote }}, value: {{ $v | quote }}}
{{- end }}
{{- end -}}

{{/* Pod-level volumes + container mounts shared by app and migration Job */}}
{{- define "app.volumes" -}}
- name: tmp
  emptyDir: {sizeLimit: 64Mi}
{{- if include "app.hasSecrets" . }}
- name: secrets
  csi:
    driver: secrets-store.csi.k8s.io
    readOnly: true
    volumeAttributes:
      secretProviderClass: {{ include "app.fullname" . }}
{{- end }}
{{- end -}}

{{- define "app.volumeMounts" -}}
- {name: tmp, mountPath: /tmp}
{{- if include "app.hasSecrets" . }}
- {name: secrets, mountPath: {{ .Values.keyVault.mountPath }}, readOnly: true}
{{- end }}
{{- end -}}
