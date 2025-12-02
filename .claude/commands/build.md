# Build Immagini Docker

Builda le immagini Docker per linux/amd64 (compatibile con server cloud).

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

### Step 3: Esegui build

**Per variante base:**
```bash
podman build --platform linux/amd64 \
  -t ghcr.io/strawberry-code/ragify:{version} \
  -t ghcr.io/strawberry-code/ragify:latest \
  -f Dockerfile .
```

**Per variante tika:**
```bash
podman build --platform linux/amd64 \
  -t ghcr.io/strawberry-code/ragify:{version}-tika \
  -t ghcr.io/strawberry-code/ragify:latest-tika \
  -f Dockerfile.tika .
```

### Step 4: Verifica

```bash
podman images | grep ragify
```

### Step 5: Output

Mostra:
- Tag creati
- Dimensione immagini
- Prossimo comando: `/push-ghcr` o `/push-ghcr {version}`

---

## Esempio

```
/build 1.1.0

Building ragify:1.1.0-tika...
✓ ghcr.io/strawberry-code/ragify:1.1.0-tika
✓ ghcr.io/strawberry-code/ragify:latest-tika

Prossimo step: /push-ghcr 1.1.0
```

---

## Note

- Build usa `--platform linux/amd64` per compatibilità server
- Il build può richiedere 5-10 minuti
- Se il build fallisce per rete, riprovare
- Usa `podman` (o `docker` se non disponibile)
