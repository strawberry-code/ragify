# Build Immagini Docker Multi-Arch

Builda le immagini Docker compatibili con linux/amd64 (server) e linux/arm64 (Mac M1/M2).

## Istruzioni

1. Chiedi all'utente quale variante buildare:
   - `base` - Dockerfile (senza Tika, solo text/code)
   - `tika` - Dockerfile.tika (con Java/Tika per PDF/Office)
   - `both` - Entrambe

2. Chiedi la versione tag (es. `1.0.2`) oppure usa `latest`

3. Esegui il build con podman/docker:

### Per variante base:
```bash
podman build --platform linux/amd64 \
  -t ghcr.io/strawberry-code/ragify:latest \
  -t ghcr.io/strawberry-code/ragify:{version} \
  -f Dockerfile .
```

### Per variante tika:
```bash
podman build --platform linux/amd64 \
  -t ghcr.io/strawberry-code/ragify:latest-tika \
  -t ghcr.io/strawberry-code/ragify:{version}-tika \
  -f Dockerfile.tika .
```

## Note

- Il build usa `--platform linux/amd64` per compatibilità con server cloud (Azure, AWS, GCP)
- Il build può richiedere 5-10 minuti per la variante tika (download Ollama model + Tika JAR)
- Se il build fallisce per problemi di rete, riprovare

## Output atteso

Al termine mostra:
- Tag delle immagini create
- Dimensione approssimativa
- Prossimo step: `/push-ghcr` per pubblicare
