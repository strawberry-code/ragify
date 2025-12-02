# Push Immagini su GitHub Container Registry

Pubblica le immagini Docker su ghcr.io/strawberry-code/ragify.

## Prerequisiti

- Essere loggati a GHCR: `podman login ghcr.io -u USERNAME`
- Immagini già buildate con `/build`

## Istruzioni

1. Lista le immagini locali disponibili:
```bash
podman images | grep ragify
```

2. Chiedi all'utente quali immagini pushare:
   - `latest` - Solo tag latest
   - `latest-tika` - Solo variante tika
   - `all` - Tutte le immagini ragify

3. Esegui il push:

### Push singola immagine:
```bash
podman push ghcr.io/strawberry-code/ragify:latest
podman push ghcr.io/strawberry-code/ragify:latest-tika
```

### Push con versione specifica:
```bash
podman push ghcr.io/strawberry-code/ragify:{version}
podman push ghcr.io/strawberry-code/ragify:{version}-tika
```

## Troubleshooting

Se il push fallisce con errore TLS:
```bash
podman push --tls-verify=false ghcr.io/strawberry-code/ragify:latest-tika
```

Se fallisce per autenticazione:
```bash
podman login ghcr.io -u strawberry-code
# Inserire Personal Access Token con scope: write:packages
```

## Output atteso

Al termine mostra:
- URL delle immagini pubblicate
- Comando per pull: `docker pull ghcr.io/strawberry-code/ragify:latest-tika`
- Prossimo step: aggiornare docker-compose.yml sul server
