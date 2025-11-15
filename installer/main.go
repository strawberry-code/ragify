package main

import (
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"syscall"
	"time"

	"github.com/charmbracelet/bubbles/progress"
	"github.com/charmbracelet/bubbles/spinner"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// Styles
var (
	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#FF69B4")).
			MarginLeft(2)

	subtitleStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#7D56F4")).
			MarginLeft(2)

	helpStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#626262")).
			MarginLeft(2)

	selectedStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FF69B4")).
			Bold(true)

	checkboxStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#00FF00"))

	errorStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FF0000")).
			Bold(true)

	successStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#00FF00")).
			Bold(true)

	warningStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FFA500")).
			Bold(true)
)

type screen int

const (
	welcomeScreen screen = iota
	checkScreen
	selectScreen
	installScreen
	configScreen
	completeScreen
)

type model struct {
	currentScreen  screen
	cursor         int
	checks         map[string]bool
	selected       map[string]bool
	installing     bool
	installStep    string
	installStatus  map[string]string
	err            error
	width          int
	height         int
	spinner        spinner.Model
	progress       progress.Model
	configClient   string
	configApiKey   string
	installLogs    []string
}

type checkResult struct {
	component string
	installed bool
}

type installStepMsg struct {
	component string
	status    string
	err       error
}

type installComplete struct{}

func initialModel() model {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("#FF69B4"))

	return model{
		currentScreen: welcomeScreen,
		cursor:        0,
		checks:        make(map[string]bool),
		selected: map[string]bool{
			"docker":      true,
			"ollama":      true,
			"qdrant":      true,
			"mcp_server":  true,
			"python_deps": true,
		},
		installing:    false,
		installStatus: make(map[string]string),
		spinner:       s,
		progress:      progress.New(progress.WithDefaultGradient()),
		installLogs:   []string{},
	}
}

func (m model) Init() tea.Cmd {
	return m.spinner.Tick
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "q":
			if m.currentScreen != installScreen {
				return m, tea.Quit
			}
		case "enter":
			return m.handleEnter()
		case "up", "k":
			if m.cursor > 0 {
				m.cursor--
			}
		case "down", "j":
			maxCursor := m.getMaxCursor()
			if m.cursor < maxCursor {
				m.cursor++
			}
		case " ":
			return m.handleSpace()
		}

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.progress.Width = msg.Width - 6

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd

	case checkResult:
		m.checks[msg.component] = msg.installed
		if len(m.checks) >= 5 {
			time.Sleep(500 * time.Millisecond)
			m.currentScreen = selectScreen
			m.cursor = 0
		} else {
			return m, m.runNextCheck()
		}

	case installStepMsg:
		m.installStatus[msg.component] = msg.status
		if msg.err != nil {
			m.installLogs = append(m.installLogs, fmt.Sprintf("❌ %s: %v", msg.component, msg.err))
		} else {
			m.installLogs = append(m.installLogs, fmt.Sprintf("✓ %s: %s", msg.component, msg.status))
		}
		return m, m.runNextInstall()

	case installComplete:
		m.currentScreen = configScreen
		m.cursor = 0
	}

	return m, nil
}

func (m model) handleEnter() (tea.Model, tea.Cmd) {
	switch m.currentScreen {
	case welcomeScreen:
		m.currentScreen = checkScreen
		return m, m.runChecks()
	case selectScreen:
		m.currentScreen = installScreen
		m.installing = true
		return m, tea.Batch(m.spinner.Tick, m.runInstallation())
	case configScreen:
		if m.cursor == 3 { // Skip
			m.currentScreen = completeScreen
		} else {
			// TODO: implement client config
			m.currentScreen = completeScreen
		}
		return m, nil
	case completeScreen:
		return m, tea.Quit
	}
	return m, nil
}

func (m model) handleSpace() (tea.Model, tea.Cmd) {
	if m.currentScreen == selectScreen {
		components := []string{"docker", "ollama", "qdrant", "mcp_server", "python_deps"}
		if m.cursor < len(components) {
			component := components[m.cursor]
			m.selected[component] = !m.selected[component]
		}
	}
	return m, nil
}

func (m model) getMaxCursor() int {
	switch m.currentScreen {
	case selectScreen:
		return 4
	case configScreen:
		return 3
	default:
		return 0
	}
}

func (m model) runChecks() tea.Cmd {
	return func() tea.Msg {
		return checkResult{component: "docker", installed: checkDocker()}
	}
}

func (m model) runNextCheck() tea.Cmd {
	return func() tea.Msg {
		switch len(m.checks) {
		case 1:
			return checkResult{component: "ollama", installed: checkOllama()}
		case 2:
			return checkResult{component: "nodejs", installed: checkNodeJS()}
		case 3:
			return checkResult{component: "python", installed: checkPython()}
		case 4:
			return checkResult{component: "disk", installed: checkDiskSpace()}
		}
		return nil
	}
}

var installQueue []string

func (m model) runInstallation() tea.Cmd {
	return func() tea.Msg {
		installQueue = []string{}
		for component, selected := range m.selected {
			if selected && !m.checks[component] {
				installQueue = append(installQueue, component)
			}
		}
		if len(installQueue) == 0 {
			return installComplete{}
		}
		return m.installNext()()
	}
}

func (m model) runNextInstall() tea.Cmd {
	return func() tea.Msg {
		if len(installQueue) > 0 {
			return m.installNext()()
		}
		return installComplete{}
	}
}

func (m model) installNext() tea.Cmd {
	return func() tea.Msg {
		if len(installQueue) == 0 {
			return installComplete{}
		}
		
		component := installQueue[0]
		installQueue = installQueue[1:]
		
		var err error
		var status string
		
		switch component {
		case "docker":
			status, err = installDocker()
		case "ollama":
			status, err = installOllama()
		case "qdrant":
			status, err = installQdrant()
		case "mcp_server":
			status, err = installMCPServer()
		case "python_deps":
			status, err = installPythonDeps()
		}
		
		return installStepMsg{component: component, status: status, err: err}
	}
}

// Check functions
func checkDocker() bool {
	cmd := exec.Command("docker", "--version")
	return cmd.Run() == nil
}

func checkOllama() bool {
	resp, err := http.Get("http://localhost:11434/api/tags")
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == 200
}

func checkNodeJS() bool {
	cmd := exec.Command("node", "--version")
	out, err := cmd.Output()
	if err != nil {
		return false
	}
	version := strings.TrimSpace(string(out))
	return strings.HasPrefix(version, "v")
}

func checkPython() bool {
	cmd := exec.Command("python3", "--version")
	out, err := cmd.Output()
	if err != nil {
		return false
	}
	version := strings.TrimSpace(string(out))
	return strings.Contains(version, "Python 3.")
}

func checkDiskSpace() bool {
	var stat syscall.Statfs_t
	err := syscall.Statfs("/", &stat)
	if err != nil {
		return false
	}
	available := stat.Bavail * uint64(stat.Bsize)
	fiveGB := uint64(5 * 1024 * 1024 * 1024)
	return available > fiveGB
}

// Install functions
func installDocker() (string, error) {
	goos := runtime.GOOS
	switch goos {
	case "darwin":
		return "Please install Docker Desktop from docker.com/products/docker-desktop", fmt.Errorf("manual installation required")
	case "linux":
		cmd := exec.Command("sh", "-c", "curl -fsSL https://get.docker.com | sh")
		err := cmd.Run()
		if err != nil {
			return "Failed", err
		}
		return "Installed via get.docker.com", nil
	default:
		return "Unsupported OS", fmt.Errorf("unsupported operating system: %s", goos)
	}
}

func installOllama() (string, error) {
	goos := runtime.GOOS
	switch goos {
	case "darwin":
		return "Please download from ollama.ai/download", fmt.Errorf("manual installation required")
	case "linux":
		cmd := exec.Command("sh", "-c", "curl -fsSL https://ollama.ai/install.sh | sh")
		err := cmd.Run()
		if err != nil {
			return "Failed", err
		}
		// Pull the embedding model
		pullCmd := exec.Command("ollama", "pull", "nomic-embed-text")
		if err := pullCmd.Run(); err != nil {
			return "Installed but model pull failed", err
		}
		return "Installed with nomic-embed-text", nil
	default:
		return "Unsupported OS", fmt.Errorf("unsupported operating system: %s", goos)
	}
}

func installQdrant() (string, error) {
	cmd := exec.Command("docker", "run", "-d",
		"--name", "qdrant",
		"-p", "6333:6333",
		"-p", "6334:6334",
		"-v", "./qdrant_storage:/qdrant/storage",
		"qdrant/qdrant:latest")
	
	output, err := cmd.CombinedOutput()
	if err != nil {
		if strings.Contains(string(output), "already in use") {
			return "Already running", nil
		}
		return "Failed", err
	}
	
	time.Sleep(2 * time.Second)
	return "Started in Docker", nil
}

func installMCPServer() (string, error) {
	cmd := exec.Command("npm", "install", "-g", "@qpd-v/mcp-server-ragdocs")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return "Failed: " + string(output), err
	}
	return "Installed globally via npm", nil
}

func installPythonDeps() (string, error) {
	cmd := exec.Command("pip3", "install", "-r", "../requirements.txt")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return "Failed: " + string(output), err
	}
	return "Installed via pip3", nil
}

func (m model) View() string {
	switch m.currentScreen {
	case welcomeScreen:
		return m.welcomeView()
	case checkScreen:
		return m.checkView()
	case selectScreen:
		return m.selectView()
	case installScreen:
		return m.installView()
	case configScreen:
		return m.configView()
	case completeScreen:
		return m.completeView()
	}
	return ""
}

func (m model) welcomeView() string {
	s := "\n"
	s += titleStyle.Render("🚀 Self-Hosted RAG Platform Installer") + "\n\n"
	s += subtitleStyle.Render("Welcome to the interactive installation wizard!") + "\n\n"
	s += lipgloss.NewStyle().MarginLeft(2).Render(
		"This installer will help you set up:\n" +
			"  • Qdrant (Vector Database)\n" +
			"  • Ollama (Embeddings Model)\n" +
			"  • MCP Server (Query Interface)\n" +
			"  • Python Dependencies\n" +
			"  • Optional: Client Configuration\n",
	) + "\n\n"
	s += helpStyle.Render("Press Enter to start • q to quit") + "\n"
	return s
}

func (m model) checkView() string {
	s := "\n"
	s += titleStyle.Render("🔍 Checking System Requirements") + "\n\n"

	components := []struct {
		name string
		key  string
	}{
		{"Docker", "docker"},
		{"Ollama", "ollama"},
		{"Node.js", "nodejs"},
		{"Python 3.8+", "python"},
		{"Disk Space (5GB+)", "disk"},
	}

	for _, comp := range components {
		status := m.spinner.View() + " Checking..."
		if installed, ok := m.checks[comp.key]; ok {
			if installed {
				status = checkboxStyle.Render("✓ Installed")
			} else {
				status = warningStyle.Render("⚠ Not found (will install)")
			}
		}
		s += lipgloss.NewStyle().MarginLeft(2).Render(
			fmt.Sprintf("%-20s %s\n", comp.name, status),
		)
	}

	s += "\n" + helpStyle.Render("Scanning system...") + "\n"
	return s
}

func (m model) selectView() string {
	s := "\n"
	s += titleStyle.Render("📦 Select Components to Install") + "\n\n"

	components := []struct {
		name string
		key  string
		desc string
	}{
		{"Docker", "docker", "Required for Qdrant"},
		{"Ollama", "ollama", "Required for embeddings (nomic-embed-text)"},
		{"Qdrant", "qdrant", "Vector database (Docker container)"},
		{"MCP Server", "mcp_server", "Query interface (@qpd-v/mcp-server-ragdocs)"},
		{"Python Deps", "python_deps", "requests + beautifulsoup4"},
	}

	for i, comp := range components {
		cursor := " "
		if m.cursor == i {
			cursor = ">"
		}

		checkbox := "☐"
		if m.selected[comp.key] {
			checkbox = checkboxStyle.Render("☑")
		}

		// Show if already installed
		installed := ""
		if m.checks[comp.key] {
			installed = checkboxStyle.Render(" (already installed)")
		}

		line := fmt.Sprintf("%s %s %-15s %s%s", cursor, checkbox, comp.name, comp.desc, installed)
		if m.cursor == i {
			line = selectedStyle.Render(line)
		}
		s += lipgloss.NewStyle().MarginLeft(2).Render(line) + "\n"
	}

	s += "\n" + helpStyle.Render("↑/↓: navigate • space: toggle • enter: install • q: quit") + "\n"
	return s
}

func (m model) installView() string {
	s := "\n"
	s += titleStyle.Render("⚙️  Installing Components") + "\n\n"

	if len(m.installLogs) > 0 {
		for _, log := range m.installLogs {
			s += lipgloss.NewStyle().MarginLeft(2).Render(log) + "\n"
		}
	} else {
		s += lipgloss.NewStyle().MarginLeft(2).Render(m.spinner.View() + " Starting installation...") + "\n"
	}

	s += "\n" + helpStyle.Render("Please wait... (this may take a few minutes)") + "\n"
	return s
}

func (m model) configView() string {
	s := "\n"
	s += titleStyle.Render("🔧 Configure MCP Client") + "\n\n"

	clients := []string{
		"Crush (requires Anthropic API key)",
		"Claude Desktop (macOS app)",
		"Cline (VS Code extension)",
		"Skip configuration (manual setup)",
	}

	for i, client := range clients {
		cursor := " "
		if m.cursor == i {
			cursor = ">"
		}

		line := fmt.Sprintf("%s %s", cursor, client)
		if m.cursor == i {
			line = selectedStyle.Render(line)
		}
		s += lipgloss.NewStyle().MarginLeft(2).Render(line) + "\n"
	}

	s += "\n" + helpStyle.Render("↑/↓: navigate • enter: select • q: quit") + "\n"
	s += "\n" + warningStyle.Render("Note: Configuration files will be created/updated") + "\n"
	return s
}

func (m model) completeView() string {
	s := "\n"
	s += successStyle.Render("✨ Installation Complete!") + "\n\n"

	s += lipgloss.NewStyle().MarginLeft(2).Render(
		"Your RAG platform is ready to use!\n\n" +
			"Quick start:\n" +
			"  1. Index documentation:\n" +
			"     cd /Users/ccavo001/github/strawberry-code/self-hosted-llm-rag\n" +
			"     python3 docs_server.py /path/to/docs --port 8000 &\n" +
			"     python3 local_docs_url_generator.py /path/to/docs -o urls.txt\n" +
			"     python3 add_urls_to_qdrant.py urls.txt\n\n" +
			"  2. Query via MCP (in Crush or other client):\n" +
			"     mcp_ragdocs_search_documentation query=\"your question\" limit=5\n\n" +
			"  3. Test system:\n" +
			"     python3 test_ragdocs.py\n\n" +
			"Read README.md for full documentation.\n",
	) + "\n"

	s += helpStyle.Render("Press Enter to exit") + "\n"
	return s
}

func main() {
	p := tea.NewProgram(initialModel())
	if _, err := p.Run(); err != nil {
		fmt.Printf("Error: %v\n", err)
		os.Exit(1)
	}
}
