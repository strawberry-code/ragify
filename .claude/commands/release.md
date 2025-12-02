# Release Completa

Esegue in sequenza: commit release, build, push GHCR, crea GitHub Release.

## Sintassi

```
/release patch      # Release patch: 1.2.3 → 1.2.4
/release minor      # Release minor: 1.2.3 → 1.3.0
/release major      # Release major: 1.2.3 → 2.0.0
```

## Argomento: $ARGUMENTS

**RICHIESTO:** Deve essere `patch`, `minor`, o `major`.

---

## Flusso

### Step 1: Pre-check

```bash
git status
git log -1 --oneline
```

Verifica:
- Nessuna modifica non committata (o chiedi di includerle)
- Branch è `main`

### Step 2: Leggi versione corrente

```bash
# Da CHANGELOG.md, trova primo ## [x.y.z]
grep -E '## \[[0-9]+\.[0-9]+\.[0-9]+\]' CHANGELOG.md | head -1
```

Calcola nuova versione in base all'argomento.

### Step 3: Mostra piano

```
=== RELEASE PLAN ===
Versione corrente: 1.0.0
Nuova versione:    1.1.0
Tipo:              minor

Azioni:
1. Aggiorna CHANGELOG.md (Unreleased → 1.1.0)
2. Commit: chore(release): rilascia versione 1.1.0
3. Tag: v1.1.0
4. Push: origin/main + tag
5. Build: ragify:1.1.0-tika
6. Push GHCR: ghcr.io/strawberry-code/ragify:1.1.0-tika
7. GitHub Release: v1.1.0 con note da CHANGELOG

Procedere? [y/N]
```

### Step 4: Esegui release

**4.1 Aggiorna CHANGELOG.md**
- Rinomina `## [Unreleased]` → `## [nuova_versione] - YYYY-MM-DD`
- Aggiungi nuova sezione `## [Unreleased]` vuota

**4.2 Commit**
```bash
git add -A
git commit -m "chore(release): rilascia versione {version}"
```

**4.3 Tag**
```bash
git tag v{version}
```

**4.4 Push git**
```bash
git push origin main
git push origin v{version}
```

**4.5 Build Docker**
```bash
podman build --platform linux/amd64 \
  -t ghcr.io/strawberry-code/ragify:{version}-tika \
  -t ghcr.io/strawberry-code/ragify:latest-tika \
  -f Dockerfile.tika .
```

**4.6 Push GHCR**
```bash
podman push ghcr.io/strawberry-code/ragify:{version}-tika
podman push ghcr.io/strawberry-code/ragify:latest-tika
```

Se errore TLS, usa `--tls-verify=false`.

**4.7 Crea GitHub Release**

Estrai le note dalla sezione appena rilasciata in CHANGELOG.md e crea la release:

```bash
gh release create v{version} --title "v{version}" --notes "$(cat <<'EOF'
## What's Changed

### Added
- [contenuto da CHANGELOG ### Added]

### Changed
- [contenuto da CHANGELOG ### Changed]

### Fixed
- [contenuto da CHANGELOG ### Fixed]

### Docker Images
- `ghcr.io/strawberry-code/ragify:{version}-tika`
- `ghcr.io/strawberry-code/ragify:latest-tika`
EOF
)"
```

### Step 5: Riepilogo finale

```
=== RELEASE v1.1.0 COMPLETATA ===

Git:
  Commit: abc1234 "chore(release): rilascia versione 1.1.0"
  Tag: v1.1.0
  Remote: origin/main

Docker:
  ghcr.io/strawberry-code/ragify:1.1.0-tika
  ghcr.io/strawberry-code/ragify:latest-tika

GitHub Release:
  https://github.com/strawberry-code/ragify/releases/tag/v1.1.0

Deploy:
  docker pull ghcr.io/strawberry-code/ragify:latest-tika
  docker compose down && docker compose up -d
```

---

## Note

- Richiede conferma prima di procedere
- Se un passaggio fallisce, si ferma e chiede come procedere
- Il processo completo richiede ~10-15 minuti
- Builda solo variante `-tika` (la più usata)
- Le note della GitHub Release vengono estratte dal CHANGELOG.md
