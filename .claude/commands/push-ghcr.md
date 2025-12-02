# Push Immagini su GitHub Container Registry

Pubblica le immagini Docker su ghcr.io/strawberry-code/ragify.

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

### Step 2: Lista immagini disponibili

```bash
podman images | grep ragify
```

Verifica che le immagini da pushare esistano.

### Step 3: Esegui push

**Se versione specifica (es. 1.1.0):**
```bash
# Base image
podman push ghcr.io/strawberry-code/ragify:{version}
podman push ghcr.io/strawberry-code/ragify:latest

# Tika image
podman push ghcr.io/strawberry-code/ragify:{version}-tika
podman push ghcr.io/strawberry-code/ragify:latest-tika
```

**Se solo latest:**
```bash
podman push ghcr.io/strawberry-code/ragify:latest
podman push ghcr.io/strawberry-code/ragify:latest-tika
```

### Step 4: Verifica tag git

Se è stata fatta una release con `/commit patch|minor|major`, verifica che il tag git sia stato pushato:

```bash
git tag -l | tail -5
git ls-remote --tags origin | tail -5
```

Se il tag locale esiste ma non è su origin, chiedi se pusharlo:
```bash
git push origin v{version}
```

### Step 5: Output

Mostra:
- Immagini pubblicate
- URL GHCR: `ghcr.io/strawberry-code/ragify`
- Comando pull: `docker pull ghcr.io/strawberry-code/ragify:latest-tika`
- Comandi per deploy su server

---

## Troubleshooting

**Errore TLS:**
```bash
podman push --tls-verify=false ghcr.io/strawberry-code/ragify:latest-tika
```

**Errore autenticazione:**
```bash
podman login ghcr.io -u strawberry-code
# Token: ghp_... (con scope write:packages)
```

---

## Esempio

```
/push-ghcr 1.1.0

Pushing images...
✓ ghcr.io/strawberry-code/ragify:1.1.0
✓ ghcr.io/strawberry-code/ragify:latest
✓ ghcr.io/strawberry-code/ragify:1.1.0-tika
✓ ghcr.io/strawberry-code/ragify:latest-tika

Git tag v1.1.0 pushed to origin.

Deploy su server:
  docker pull ghcr.io/strawberry-code/ragify:latest-tika
  docker compose down && docker compose up -d
```
