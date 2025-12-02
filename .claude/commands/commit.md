# Commit con Conventional Changelog e Semver

Esegui un commit seguendo Conventional Commits con supporto opzionale per release semver.

## Sintassi

```
/commit              # Commit normale, aggiunge a [Unreleased]
/commit patch        # Release patch: 1.2.3 → 1.2.4
/commit minor        # Release minor: 1.2.3 → 1.3.0
/commit major        # Release major: 1.2.3 → 2.0.0
```

## Argomento: $ARGUMENTS

---

## Istruzioni

### Step 1: Analizza le modifiche

```bash
git status
git diff --staged
git diff
```

Se non ci sono file staged, chiedi all'utente quali file aggiungere.

### Step 2: Determina tipo commit

Analizza le modifiche e determina:
- `feat`: nuova funzionalità
- `fix`: correzione bug
- `docs`: documentazione
- `style`: formattazione
- `refactor`: refactoring
- `test`: test
- `chore`: manutenzione

Scope: `api`, `frontend`, `docker`, `lib`, `mcp`, `cli`, `docs`

### Step 3: Scrivi messaggio

Messaggio in italiano, massimo 30 parole, descrittivo.

### Step 4: Gestisci CHANGELOG

**Se NESSUN argomento (commit normale):**

1. Leggi CHANGELOG.md
2. Aggiungi entry sotto `## [Unreleased]` nella sezione appropriata:
   - `### Added` - nuove funzionalità
   - `### Changed` - modifiche
   - `### Fixed` - bug fix
   - `### Removed` - rimozioni

**Se argomento `patch`, `minor`, o `major`:**

1. Leggi CHANGELOG.md e trova versione corrente (primo `## [x.y.z]`)
2. Calcola nuova versione:
   - `patch`: incrementa z (1.2.3 → 1.2.4)
   - `minor`: incrementa y, azzera z (1.2.3 → 1.3.0)
   - `major`: incrementa x, azzera y e z (1.2.3 → 2.0.0)
3. Rinomina `## [Unreleased]` in `## [nuova_versione] - YYYY-MM-DD`
4. Aggiungi nuova sezione `## [Unreleased]` vuota sopra
5. Prepara tag git: `v{nuova_versione}`

### Step 5: Esegui commit

```bash
git add -A  # o file specifici
git commit -m "type(scope): messaggio"
```

### Step 6: Se release (patch/minor/major)

```bash
# Crea tag
git tag v{nuova_versione}

# Mostra comandi per push (NON eseguire automaticamente)
echo "Per completare la release:"
echo "  git push origin main"
echo "  git push origin v{nuova_versione}"
```

**NON fare push automaticamente. Mostra i comandi e chiedi conferma.**

---

## Esempio: Commit normale

```bash
# Input: /commit
# Modifica CHANGELOG.md aggiungendo sotto [Unreleased]:
### Added
- Nuovo endpoint per batch upload

git add -A
git commit -m "feat(api): aggiunge endpoint per batch upload di file multipli"
```

## Esempio: Release minor

```bash
# Input: /commit minor
# Versione attuale: 1.0.0
# Nuova versione: 1.1.0

# CHANGELOG.md prima:
## [Unreleased]
### Added
- Feature X
- Feature Y

## [1.0.0] - 2025-12-01
...

# CHANGELOG.md dopo:
## [Unreleased]

## [1.1.0] - 2025-12-02
### Added
- Feature X
- Feature Y

## [1.0.0] - 2025-12-01
...

git add -A
git commit -m "chore(release): rilascia versione 1.1.0"
git tag v1.1.0

echo "Per completare: git push origin main && git push origin v1.1.0"
```

---

## Note

- Il messaggio di release è sempre `chore(release): rilascia versione X.Y.Z`
- I tag seguono formato `vX.Y.Z` (con v prefisso)
- NON pushare automaticamente, chiedi sempre conferma
- Se [Unreleased] è vuoto, avvisa l'utente prima di fare release
