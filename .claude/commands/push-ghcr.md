# Push Immagini Multi-Arch su GitHub Container Registry

Pubblica le immagini Docker multi-architettura su ghcr.io/strawberry-code/ragify.

## Sintassi

```
/push-ghcr              # Push latest tags
/push-ghcr 1.2.0        # Push versione specifica + latest
```

## Argomento: $ARGUMENTS

---

## Prerequisiti

Verifica login a GHCR:
```bash
podman login ghcr.io -u strawberry-code
# Personal Access Token con scope: write:packages
```

---

## Istruzioni

### Step 1: Determina versione

**Se argomento fornito:** push quella versione + latest

**Se NESSUN argomento:** push solo latest

### Step 2: Verifica immagini e manifest

```bash
# Lista immagini locali
podman images | grep ragify

# Verifica manifest esistenti
podman manifest inspect ghcr.io/strawberry-code/ragify:{version}-tika 2>/dev/null
```

### Step 3: Esegui push dei manifest multi-arch

**Se versione specifica (es. 1.1.3):**
```bash
# Push manifest multi-arch (include arm64 + amd64)
podman manifest push ghcr.io/strawberry-code/ragify:{version}-tika \
  docker://ghcr.io/strawberry-code/ragify:{version}-tika

podman manifest push ghcr.io/strawberry-code/ragify:latest-tika \
  docker://ghcr.io/strawberry-code/ragify:latest-tika
```

**Se solo latest:**
```bash
podman manifest push ghcr.io/strawberry-code/ragify:latest-tika \
  docker://ghcr.io/strawberry-code/ragify:latest-tika
```

### Step 4: Verifica su GHCR

```bash
# Verifica manifest remoto
podman manifest inspect docker://ghcr.io/strawberry-code/ragify:{version}-tika
```

Dovresti vedere entrambe le architetture:
- `linux/amd64`
- `linux/arm64`

### Step 5: Verifica tag git

Se è stata fatta una release con `/commit patch|minor|major`, verifica che il tag git sia stato pushato:

```bash
git tag -l | tail -5
git ls-remote --tags origin | tail -5
```

Se il tag locale esiste ma non è su origin, chiedi se pusharlo:
```bash
git push origin v{version}
```

### Step 6: Output

Mostra:
- Manifest pubblicati con architetture supportate
- URL GHCR: `ghcr.io/strawberry-code/ragify`
- Comando pull: `docker pull ghcr.io/strawberry-code/ragify:latest-tika`
- Nota: Docker/Podman seleziona automaticamente l'architettura corretta

---

## Troubleshooting

**Errore TLS:**
```bash
podman manifest push --tls-verify=false ghcr.io/strawberry-code/ragify:latest-tika \
  docker://ghcr.io/strawberry-code/ragify:latest-tika
```

**Errore autenticazione:**
```bash
podman login ghcr.io -u strawberry-code
# Token: ghp_... (con scope write:packages)
```

**Manifest non trovato:**
Prima esegui `/build {version}` per creare le immagini e i manifest.

---

## Esempio

```
/push-ghcr 1.1.3

Pushing multi-arch manifests...
✓ ghcr.io/strawberry-code/ragify:1.1.3-tika (linux/amd64, linux/arm64)
✓ ghcr.io/strawberry-code/ragify:latest-tika (linux/amd64, linux/arm64)

Git tag v1.1.3 pushed to origin.

Deploy su server (Ubuntu o Mac):
  docker pull ghcr.io/strawberry-code/ragify:latest-tika
  docker compose down && docker compose up -d

L'architettura corretta viene selezionata automaticamente.
```
