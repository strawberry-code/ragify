# Release Completa

Esegue in sequenza: commit, build, push su GHCR.

## Flusso

### Step 1: Commit
- Verifica modifiche pendenti
- Aggiorna CHANGELOG.md
- Commit con conventional commits
- Push su GitHub

### Step 2: Build
- Chiedi versione (es. `1.0.2`)
- Build immagine base (Dockerfile)
- Build immagine tika (Dockerfile.tika)
- Usa `--platform linux/amd64`

### Step 3: Push GHCR
- Push tutte le immagini buildate
- Verifica upload completato

### Step 4: Tag Git (opzionale)
- Chiedi se creare tag git: `v{version}`
- Se sì: `git tag v{version} && git push --tags`

## Istruzioni

1. **Prima di iniziare**, mostra lo stato attuale:
```bash
git status
git log -1 --oneline
podman images | grep ragify
```

2. **Chiedi conferma** per procedere con la release

3. **Chiedi la versione** da rilasciare (es. `1.0.2`)

4. **Esegui sequenzialmente**:
   - Commit (se ci sono modifiche)
   - Build entrambe le varianti
   - Push su GHCR
   - Tag git (se confermato)

5. **Al termine**, mostra riepilogo:
   - Commit hash
   - Tag git (se creato)
   - Immagini pubblicate
   - Comandi per deploy su server

## Esempio output finale

```
=== RELEASE v1.0.2 COMPLETATA ===

Git:
  - Commit: a1b2c3d "feat(docker): ..."
  - Tag: v1.0.2
  - Push: origin/main

Docker Images:
  - ghcr.io/strawberry-code/ragify:1.0.2
  - ghcr.io/strawberry-code/ragify:latest
  - ghcr.io/strawberry-code/ragify:1.0.2-tika
  - ghcr.io/strawberry-code/ragify:latest-tika

Deploy su server:
  docker pull ghcr.io/strawberry-code/ragify:latest-tika
  docker compose down && docker compose up -d
```

## Note

- NON procedere senza conferma esplicita dell'utente ad ogni step
- Se un passaggio fallisce, fermarsi e chiedere come procedere
- Il processo completo può richiedere 10-15 minuti
