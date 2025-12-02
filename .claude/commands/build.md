# Build Immagini Docker Multi-Architettura

Builda le immagini Docker per linux/amd64 (Ubuntu/cloud) e linux/arm64 (Mac M1/M2).

## Sintassi

```
/build              # Build con versione da git tag
/build 1.2.0        # Build con versione specifica
```

## Argomento: $ARGUMENTS

---

## Istruzioni

### Step 1: Determina versione

**Se argomento fornito:** usa quella versione

**Se NESSUN argomento:**
```bash
# Prendi ultimo tag git
git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0"
```

Rimuovi il prefisso `v` per ottenere la versione (es. `v1.2.0` → `1.2.0`).

### Step 2: Chiedi variante

Chiedi all'utente quale variante buildare:
- `base` - Dockerfile (senza Tika, ~3GB)
- `tika` - Dockerfile.tika (con Tika per PDF, ~4GB)
- `both` - Entrambe

### Step 3: Esegui build multi-arch

Per ogni variante, builda entrambe le architetture.

**Build arm64 (nativo su Mac, veloce):**
```bash
podman build --platform linux/arm64 \
  -t ghcr.io/strawberry-code/ragify:{version}-tika-arm64 \
  -f Dockerfile.tika .
```

**Build amd64 (emulato su Mac, lento ~10 min):**
```bash
podman build --platform linux/amd64 \
  -t ghcr.io/strawberry-code/ragify:{version}-tika-amd64 \
  -f Dockerfile.tika .
```

**NOTA:** Le due build possono essere eseguite in parallelo per risparmiare tempo.

### Step 4: Crea manifest multi-arch

```bash
# Rimuovi manifest esistente se presente
podman manifest rm ghcr.io/strawberry-code/ragify:{version}-tika 2>/dev/null || true

# Crea nuovo manifest
podman manifest create ghcr.io/strawberry-code/ragify:{version}-tika

# Aggiungi le immagini
podman manifest add ghcr.io/strawberry-code/ragify:{version}-tika \
  ghcr.io/strawberry-code/ragify:{version}-tika-arm64

podman manifest add ghcr.io/strawberry-code/ragify:{version}-tika \
  ghcr.io/strawberry-code/ragify:{version}-tika-amd64

# Crea anche manifest per latest
podman manifest rm ghcr.io/strawberry-code/ragify:latest-tika 2>/dev/null || true
podman manifest create ghcr.io/strawberry-code/ragify:latest-tika
podman manifest add ghcr.io/strawberry-code/ragify:latest-tika \
  ghcr.io/strawberry-code/ragify:{version}-tika-arm64
podman manifest add ghcr.io/strawberry-code/ragify:latest-tika \
  ghcr.io/strawberry-code/ragify:{version}-tika-amd64
```

### Step 5: Verifica

```bash
podman images | grep ragify
podman manifest inspect ghcr.io/strawberry-code/ragify:{version}-tika
```

### Step 6: Output

Mostra:
- Tag creati per entrambe le architetture
- Manifest multi-arch creati
- Dimensione immagini
- Prossimo comando: `/push-ghcr` o `/push-ghcr {version}`

---

## Esempio

```
/build 1.1.3

Building ragify:1.1.3-tika (arm64 + amd64)...
✓ ghcr.io/strawberry-code/ragify:1.1.3-tika-arm64
✓ ghcr.io/strawberry-code/ragify:1.1.3-tika-amd64
✓ Manifest: ghcr.io/strawberry-code/ragify:1.1.3-tika (multi-arch)
✓ Manifest: ghcr.io/strawberry-code/ragify:latest-tika (multi-arch)

Prossimo step: /push-ghcr 1.1.3
```

---

## Note

- Build arm64 è veloce su Mac (nativo)
- Build amd64 usa emulazione QEMU (~10 min)
- Le build usano cache per layer non modificati
- Il manifest combina entrambe le architetture in un singolo tag
- Docker/Podman seleziona automaticamente l'architettura corretta al pull
