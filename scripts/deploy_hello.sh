#!/usr/bin/env bash
# Hello world do Azure Container Apps v týmové resource group.
# Předpoklad: az CLI, přihlášení týmovým účtem (az login), číslo týmu níže.
set -euo pipefail
TEAM=teamNN                      # <-- doplnit
RG=rg-$TEAM
ENV=cae-$TEAM
APP=ainor-hello

az extension add --name containerapp --upgrade -y
LOC=$(az group show -n "$RG" --query location -o tsv)
echo "Resource group $RG je v regionu $LOC"

# Prostředí bez Log Analytics (logy se účtují zvlášť)
az containerapp env create -n "$ENV" -g "$RG" -l "$LOC" --logs-destination none

# Krok A: hotový ukázkový image Microsoftu – bez registru, ověří, že nasazení funguje
az containerapp create -n "$APP" -g "$RG" --environment "$ENV" \
  --image mcr.microsoft.com/k8se/quickstart:latest \
  --target-port 80 --ingress external \
  --min-replicas 0 --max-replicas 1 --cpu 0.25 --memory 0.5Gi

az containerapp show -n "$APP" -g "$RG" --query properties.configuration.ingress.fqdn -o tsv

# Krok B (až bude image v GHCR, viz .github/workflows/build-image.yml):
# az containerapp registry set -n "$APP" -g "$RG" --server ghcr.io \
#   --username <github-user> --password <PAT s read:packages>
# az containerapp update -n "$APP" -g "$RG" --image ghcr.io/<org>/<repo>/ainor-hello:latest
# az containerapp ingress update -n "$APP" -g "$RG" --target-port 8000
