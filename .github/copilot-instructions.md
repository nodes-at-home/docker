# Copilot Instructions – Homelab Docker Stacks (`o:\docker`)

Dieses Repo enthält die Docker-Compose-Stacks des Homelabs. Sprache: **Deutsch**.

## Projektstruktur
- Ein Verzeichnis pro **Stack** (z. B. `ai/`, `admin/`, `database/`, `ems/`, `metrics/`,
  `proxy/`, `nodesathome/`, `printer3d/`, `mkdocs/`, `wsl2/`), jeweils mit eigener
  `docker-compose.yaml`.
- `bin/` enthält Helfer-Skripte (Bash): `build.sh`, `up.sh`, `startup-stacks.sh`,
  `restart.sh`, `create_networks.sh`, Registry-/Cert-/InfluxDB-Helfer u. a.
- Konfig-Dateien (z. B. `prometheus.yaml`, `traefik.yaml`, `telegraf.conf`) liegen im
  jeweiligen Stack-Verzeichnis.

## Konventionen für docker-compose.yaml
- **Images immer mit `${DOCKER_REGISTRY}`-Präfix** referenzieren (z. B.
  `image: ${DOCKER_REGISTRY}prom/prometheus`). Niemals hart auf eine Registry verdrahten.
- **`restart: ${DOCKER_RESTART_POLICY}`** statt fester Restart-Policy verwenden.
- Diese Variablen kommen aus einer **`.env`** (nicht eingecheckt). Secrets/Tokens gehören
  in `.env`, nicht in die Compose-Dateien.
- Wiederkehrende Service-Teile als **YAML-Anchor** (`x-...: &name` / `<<: *name`) definieren,
  wie bei den ollama-/whisper-/piper-Blöcken in `ai/docker-compose.yaml`.
- Persistente Daten als **Bind-Mounts unter `~/docker/<service>/...`** (siehe bestehende Stacks).
- GPU-Services: `runtime: nvidia` + Anchor `<<: *deploy_nvidia` (NVIDIA-Reservations).
- Traefik steuert den Zugriff über Labels; interne Services `traefik.enable=false`.

## Workflows (Skripte in `bin/`, laufen auf dem Docker-Host unter `~/docker/docker`)
- Stack starten: `./up.sh <stack>` · Alle Kern-Stacks: `./startup-stacks.sh`.
- Einzel-Image bauen: `./build.sh <app>` (sucht den Stack via `grep` in den Compose-Dateien).
- `docker compose` bevorzugt; Fallback `docker-compose` (Skripte erkennen das selbst).

## Image-Tagging (selbst gebaute Images)
- Schema für Jetson-Thor-Images: `r39.1.arm64-sbsa-cu132-24.04`
  (L4T-Release.arch-platform-cuda-os). Konsistent halten.

## Plattform-Hinweise
- **Thor** (AGX, sm_110/CUDA 13.2): `runtime: nvidia` nutzen, NICHT `--gpus=all`.
- **Orin NX 16 GB**: knapper Unified-Memory → dort z. B. ollama `OLLAMA_NUM_CTX=1024`.
  Auf Thor (128 GB) NICHT setzen.
- Registry `nodesathome1:5000` ist self-signed (CA `nodesathome`).

## Sicherheit / Vorsicht
- Keine Secrets, Keys oder Tokens committen (nur via `.env`).
- Nicht ungefragt auf produktive Systeme deployen oder Container/Volumes löschen.
