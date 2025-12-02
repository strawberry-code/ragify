# Changelog

Tutte le modifiche rilevanti al progetto sono documentate in questo file.

Il formato segue [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
e il progetto aderisce al [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-02

### Aggiunto
- OAuth 2.0 Authorization Server per MCP (RFC 8414, RFC 7591)
- Supporto Bearer token per autenticazione API e MCP
- Dynamic Client Registration per client MCP
- PKCE support (S256 e plain) per OAuth flow
- Frontend: status light "Authenticated" cliccabile con modal login GitHub
- Endpoint discovery `.well-known/oauth-authorization-server`
- Docker Compose example con configurazione OAuth
- Favicon SVG per frontend

### Modificato
- AuthMiddleware supporta sia session cookie che Bearer token
- Callback OAuth unificato per browser e MCP (`/oauth/github-callback`)
- Migliorata gestione errori nel middleware (JSONResponse invece di HTTPException)
- Aggiornato .gitignore per escludere docker-compose.yml e file sensibili

### Sicurezza
- Tutte le credenziali lette da variabili d'ambiente
- Session token firmati con itsdangerous
- CSRF protection con state parameter OAuth
- Whitelist utenti autorizzati via YAML
