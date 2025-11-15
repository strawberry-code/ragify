# RAG Platform Installer

Beautiful interactive TUI installer for the Self-Hosted RAG Platform, built with [Charm](https://charm.sh) tools (Bubbletea, Lipgloss, Bubbles).

## Features

✨ **Interactive Installation Wizard**
- System requirements check (Docker, Ollama, Node.js, Python, disk space)
- Component selection with checkboxes
- Real-time installation progress with spinners
- MCP client configuration wizard
- Charm.land aesthetic design

🚀 **Automated Setup**
- Docker installation (Linux auto-install, macOS guided)
- Ollama installation + nomic-embed-text model download
- Qdrant vector database in Docker
- MCP Server (@qpd-v/mcp-server-ragdocs)
- Python dependencies (requests, beautifulsoup4)

🎨 **Charm Ecosystem**
- `bubbletea` - The Elm Architecture for TUI
- `lipgloss` - Styling and layout
- `bubbles` - Spinner and progress components
- `glamour` - Markdown rendering (future use)

## Quick Start

```bash
cd installer
go build -o rag-installer
./rag-installer
```

Or build and run in one step:

```bash
cd installer && go build -o rag-installer && ./rag-installer
```

## Navigation

- `↑/↓` or `k/j` - Navigate options
- `Space` - Toggle selection (component screen)
- `Enter` - Proceed to next screen
- `q` or `Ctrl+C` - Quit (except during installation)

## Screens

### 1. Welcome
Introduction to the installer and overview of components.

### 2. System Check
Scans your system for:
- Docker (container runtime)
- Ollama (LLM embeddings)
- Node.js (MCP server)
- Python 3.8+ (utility scripts)
- Disk space (5GB+ recommended)

### 3. Component Selection
Choose what to install. Already-installed components are marked.

### 4. Installation
Runs installation commands with real-time progress. Handles:
- Platform detection (macOS vs Linux)
- Docker: automated install on Linux, guided on macOS
- Ollama: downloads embedding model automatically
- Qdrant: starts Docker container with volume mount
- MCP Server: npm global install
- Python deps: pip install from requirements.txt

### 5. Configuration
Optional MCP client setup for:
- Crush (CLI assistant)
- Claude Desktop (macOS app)
- Cline (VS Code extension)

Generates config files with correct paths and schema.

### 6. Complete
Success message with quick-start commands.

## Architecture

### The Elm Architecture (Bubbletea)

```go
type Model struct { /* application state */ }

func (m Model) Init() Cmd { /* initialize */ }
func (m Model) Update(Msg) (Model, Cmd) { /* handle events */ }
func (m Model) View() string { /* render UI */ }
```

### Message Flow

```
User Input → KeyMsg → Update() → Command execution
System Check → checkResult → Update() → Display status
Installation → installStepMsg → Update() → Progress update
```

### Component Checks

Each check runs asynchronously and returns `checkResult`:

```go
checkDocker()     // exec: docker --version
checkOllama()     // http: GET localhost:11434/api/tags
checkNodeJS()     // exec: node --version
checkPython()     // exec: python3 --version
checkDiskSpace()  // syscall: statfs "/"
```

### Installation Queue

Components are queued based on:
1. User selection (from selectScreen)
2. Not already installed (from checks)

Processed sequentially with status updates:

```go
installDocker()     → "Installed via get.docker.com"
installOllama()     → "Installed with nomic-embed-text"
installQdrant()     → "Started in Docker"
installMCPServer()  → "Installed globally via npm"
installPythonDeps() → "Installed via pip3"
```

## Styling

Color palette inspired by Charm.land:

- **Primary**: `#FF69B4` (Hot Pink) - titles, selection
- **Secondary**: `#7D56F4` (Purple) - subtitles
- **Success**: `#00FF00` (Green) - checkmarks, success
- **Warning**: `#FFA500` (Orange) - warnings
- **Error**: `#FF0000` (Red) - errors
- **Muted**: `#626262` (Gray) - help text

## Platform Support

### macOS
- Docker: Guided download of Docker Desktop
- Ollama: Guided download from ollama.ai
- MCP/Python: Automated install

### Linux
- Docker: Automated install via get.docker.com
- Ollama: Automated install + model pull
- MCP/Python: Automated install

### Windows
- Not yet supported (contributions welcome!)

## Error Handling

- **Missing dependencies**: Installer detects and offers to install
- **Port conflicts**: Graceful handling of existing Qdrant/Ollama
- **Failed installations**: Logs errors and continues with remaining components
- **Manual interventions**: Pauses for user actions (e.g., Docker.dmg install)

## Future Enhancements

- [ ] Client configuration wizard (Crush, Claude Desktop, Cline)
- [ ] Windows support
- [ ] Rollback capability on errors
- [ ] Update/uninstall mode
- [ ] Configuration file preview with Glamour
- [ ] Better progress bars for long operations
- [ ] Parallel installation where safe

## Development

### Build

```bash
go build -o rag-installer
```

### Test

```bash
go test ./...
```

### Dependencies

```bash
go mod tidy
```

### Add New Component

1. Add check function: `func checkMyComponent() bool`
2. Add install function: `func installMyComponent() (string, error)`
3. Update `runNextCheck()` to include new check
4. Update component lists in `selectView()`
5. Add case in `installNext()` switch

## License

MIT (same as parent project)

## Credits

Built with ❤️ using [Charm](https://charm.sh) tools by the amazing Charm team.
