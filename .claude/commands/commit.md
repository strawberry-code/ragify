# Commit con Conventional Changelog

Esegui un commit seguendo le linee guida Conventional Commits.

## Istruzioni

1. Esegui `git status` e `git diff --staged` per vedere le modifiche
2. Se non ci sono file staged, chiedi all'utente quali file aggiungere
3. Analizza le modifiche e determina il tipo di commit:
   - `feat`: nuova funzionalità
   - `fix`: correzione bug
   - `docs`: documentazione
   - `style`: formattazione (no logic change)
   - `refactor`: refactoring codice
   - `test`: aggiunta/modifica test
   - `chore`: manutenzione, dipendenze
4. Determina lo scope (modulo/componente modificato): `api`, `frontend`, `docker`, `lib`, `mcp`, etc.
5. Scrivi un messaggio commit in italiano, massimo 30 parole, descrittivo
6. Aggiorna il file CHANGELOG.md aggiungendo la entry sotto "## [Unreleased]"
7. Esegui il commit con formato: `type(scope): messaggio`

## Formato CHANGELOG

```markdown
## [Unreleased]

### Added
- Nuove funzionalità

### Changed
- Modifiche a funzionalità esistenti

### Fixed
- Bug fix

### Removed
- Funzionalità rimosse
```

## Esempio

```bash
git add -A
# Modifica CHANGELOG.md
git commit -m "feat(api): aggiunge endpoint per watch directories con supporto scan periodico"
```

NON fare push automaticamente. Chiedi conferma prima di ogni operazione.
