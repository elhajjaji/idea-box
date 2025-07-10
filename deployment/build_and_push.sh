#!/bin/bash
# Script de build et push Docker pour Idea Box
# Usage: ./build_and_push.sh [VERSION]

set -e

VERSION=${1:-1.0.0}
IMAGE_NAME="elhajjaji/idea-box:$VERSION"

# Build de l'image

echo "[+] Build de l'image $IMAGE_NAME ..."
docker build -t $IMAGE_NAME ..

echo "[+] Push sur Docker Hub ..."
docker push $IMAGE_NAME

echo "[OK] Image poussée : $IMAGE_NAME"
