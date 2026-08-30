#!/bin/bash

# junand 30.08.2026

# transfer_image.sh
# Übertragt ein Docker-Image von nodesathome2:5000 nach nodesathome1:5000
# Verwendet: docker pull und docker push

set -euo pipefail

# Hilfe anzeigen
show_help() {
    echo "Usage: $0 [options] IMAGE"
    echo ""
    echo "Übertragt ein Docker-Image von nodesathome2:5000 nach nodesathome1:5000"
    echo ""
    echo "Optionen:"
    echo "  -h, --help      Hilfe anzeigen"
    echo "  -i, --image     Image Name (Required, z.B. myapp:latest)"
    echo "  -f, --from      Source Registry (Standard: nodesathome2:5000)"
    echo "  -t, --to        Target Registry (Standard: nodesathome1:5000)"
    echo ""
    echo "Beispiel: $0 -i myapp:latest"
}

# Standardwerte
FROM_REGISTRY="nodesathome2:5000"
TO_REGISTRY="nodesathome1:5000"
IMAGE=""

# Parameter parsen
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -i|--image)
            IMAGE="$2"
            shift 2
            ;;
        -f|--from)
            FROM_REGISTRY="$2"
            shift 2
            ;;
        -t|--to)
            TO_REGISTRY="$2"
            shift 2
            ;;
        *)
            echo "Unbekannte Option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Image Name prüfen
if [ -z "$IMAGE" ]; then
    echo "ERROR: Image Name ist erforderlich!"
    echo "Verwenden Sie -i oder --image um das Image zu spezifizieren."
    show_help
    exit 1
fi

echo "=== Docker Image Transfer ==="
echo "Von: $FROM_REGISTRY/$IMAGE"
echo "Nach: $TO_REGISTRY/$IMAGE"
echo ""

# Image von Source Registry pullen
echo "Step 1: Pull Image von $FROM_REGISTRY/$IMAGE"
docker pull "$FROM_REGISTRY/$IMAGE"

# Image taggen für Target Registry
echo "Step 2: Tag Image für $TO_REGISTRY/$IMAGE"
docker tag "$FROM_REGISTRY/$IMAGE" "$TO_REGISTRY/$IMAGE"

# Image an Target Registry pushen
echo "Step 3: Push Image nach $TO_REGISTRY/$IMAGE"
docker push "$TO_REGISTRY/$IMAGE"

echo ""
echo "=== Transfer abgeschlossen! ==="
echo "Image $TO_REGISTRY/$IMAGE ist nun verfügbar."