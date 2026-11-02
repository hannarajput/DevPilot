# DevPilot — One-Click Development Workspace Manager

DevPilot is a native Windows desktop application built with **Python 3.12** and **CustomTkinter** designed to automate repetitive developer workflows with **Google Antigravity as the primary IDE**.

---

## 🚀 Key Capabilities

### 1. Setup Once → Launch Anytime
- **Dynamic Project Detection**: Automatically sniffs Python (`pyproject.toml`, `requirements.txt`, `*.py`), Flutter (`pubspec.yaml`, `lib/main.dart`), Node.js (`package.json`, `tsconfig.json`), and Git (`.git`) projects.
- **Laptop IDE Selection & Remember Choice**:
  - Automatically scans and displays all installed IDEs on the laptop (Antigravity IDE, Antigravity 2.0 Desktop, Microsoft VS Code, Cursor, Windsurf, JetBrains PyCharm/IntelliJ, Visual Studio, Sublime Text, or custom editors).
  - At the time of project configuration submission or initial launch, prompts the user to select their desired IDE.
  - Features a **"Remember this choice for this project"** button/checkbox: if checked, DevPilot saves this preference permanently, never prompts again for this project, and directly opens the earlier chosen IDE on future launches!
  - Users can change or reset their remembered IDE at any time directly from the project card via the **"Change IDE"** button.
- **Configurable Tasks**:
  - Target IDE workspace launcher with window reuse (`-r` / `--reuse-window`) or new window (`-n`).
  - Terminal windows (Windows Terminal `wt.exe`, PowerShell `powershell.exe`, Command Prompt `cmd.exe`) in dedicated working directories.
  - Startup commands with user approval guards.
  - Pre-flight tool version verification (`git`, `python`, `node`, `npm`, `flutter`, `wt`).
  - Web URLs, documentation portals, and supporting desktop applications.
  - Pre-flight Git repository health checks (branch name, dirty files count).
  - Reordering, enabling/disabling, and per-task editing.

### 2. Multi-Resource Project Workspace Launcher
- **Attached Workspace Resources**:
  - 🤖 **AI Conversations**: ChatGPT chat links, Claude, Gemini, Perplexity, DeepSeek, or any custom AI conversation URL.
  - 💻 **IDE / Code Editor**: Antigravity, VS Code, PyCharm, Cursor, Windsurf, or custom editors.
  - 🐙 **Websites & Repositories**: GitHub/GitLab repos, live production/staging apps, Figma canvases, Trello/Jira boards, documentation portals.
  - 📁 **Local Files & Folders**: Project directories, notes, spreadsheets, specifications opened via associated Windows applications or Explorer.
  - 🔗 **Custom URLs**: Full unrestricted support for any valid web address.
- **Dedicated Resource Management Interface**:
  - Located in the **Resources** tab of each project configuration modal.
  - Add, edit, delete, reorder (▲/▼), and enable/disable individual resources.
  - Intelligent resource type and icon auto-inference from URL or path.
  - Interactive **Test Launch** button directly in the editor.
  - Quick **+ Resource** button and resource badges strip right on each dashboard **Project Card**.
- **One-Click Unified Launch**:
  - A single click on **Launch Project** opens your IDE to the project root, opens all enabled AI chats and web URLs in separate browser tabs, and opens local files in their default apps.
  - Fault-isolated: if one resource fails, it is clearly reported in the live checklist without stopping the rest of the workspace launch.
  - Per-item **Retry** button for any failed resource or task.

### 3. One-Click Project Launch
- Prominent **Launch Project** button on every project card.
- Live task status indicators:
  - ⏳ **Queued**
  - 🔄 **Running**
  - ✅ **Success**
  - ❌ **Failed** (with an instant **Retry** button)
  - ⏭️ **Skipped**
  - ⏹️ **Stopped**
- Real-time color-coded log console with secret redaction, text search, copy, and clear features.
- Safe workflow cancellation (**Stop**) that terminates only child processes spawned by DevPilot without affecting unrelated system or editor processes.

### 4. Resume Last Session
- Remembers the last active project and active profile.
- Accessible via the top action bar: **↺ Resume Last Session [Project Name]**.
- Intelligently skips one-time setup tasks (e.g. dependency installations or migrations) while restoring workspace windows, terminals, and checks.
- Clearly states integration boundaries: restores the exact project root and configured files in Antigravity; active agent chat threads within the IDE are managed by Antigravity's internal session manager.

### 5. Automation Profiles
- **Basic Workspace**: Launches Antigravity and loads the workspace folder.
- **Development**: Launches Antigravity, interactive terminals, and development tool checks.
- **Full Workspace**: Launches Antigravity, terminals, startup services, browser URLs, and supporting apps.
- **Custom**: User-selected subset of tasks.

### 6. Enterprise Safety & Reliability
- **Command Approval Guard**: Startup commands must be explicitly approved. High-risk patterns (destructive deletion, force push, hard reset) are detected and restricted.
- **Automatic Secret Redaction**: API keys (`API_KEY=...`, Bearer tokens, AWS keys, passwords) are scrubbed from logs before display or persistence.
- **Windows Autostart**: Optional zero-privilege autostart configuration via user registry (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`).

### 7. Humanized, Minimal Design System (Light & Dark Modes)
- **Inspired by Scandinavian Editorial & Swiss Design**: Replaced saturated AI-generated neon styles with a clean, high-contrast, humanized aesthetic.
- **Monochrome & Obsidian Surfaces**: Pure porcelain canvas (`#F2F4F7`) and crisp white cards (`#FFFFFF`) with subtle 1px border lines (`#E5E7EB`) in light mode; deep obsidian (`#0E0F12`) and matte charcoal cards (`#1A1B22`) in dark mode.
- **Signature Solid Pill Controls**: High-contrast black pill buttons in light mode and silver/white pill buttons in dark mode (`corner_radius=18`).
- **Dynamic Instant Theme Switching**: Toggle between `☀️ Light` and `🌙 Dark` modes with one click in the header or through Settings with automatic persistence.
- **Overview Dashboard Banner**: Displays high-level workspace metrics (configured projects count, IDE status) directly inspired by modern executive dashboard layouts.

---

## 📁 Project Architecture

```
E:\DevPilot/
├── devpilot/
│   ├── core/
│   │   ├── antigravity.py        # Antigravity IDE / App launcher, process detection & CLI args
│   │   ├── detector.py           # Project type sniffing, tool discovery & health checks
│   │   ├── ide_detector.py       # Discovers all installed laptop IDEs & builds launch commands
│   │   ├── models.py             # Data models (ProjectConfig, ResourceConfig, IDEPreference, TaskConfig)
│   │   ├── orchestrator.py       # Async execution engine, task sequencing, cancellation, retries
│   │   ├── resource_launcher.py  # Multi-resource validation, browser tab opener, file launcher
│   │   ├── security.py           # Secret scrubbing & command safety check
│   │   ├── storage.py            # Atomic JSON persistence (%APPDATA%\DevPilot\projects.json)
│   │   ├── system.py             # Windows autostart (HKCU), browser opener, PID management
│   │   └── terminal.py           # Windows Terminal (wt), PowerShell, and CMD launchers
│   ├── ui/
│   │   ├── app.py                # Main CustomTkinter desktop window
│   │   ├── components/
│   │   │   ├── log_console.py    # Real-time searchable log console
│   │   │   ├── progress_panel.py # Task checklist, progress bar & retry controls
│   │   │   ├── project_card.py   # Interactive project cards with resource chips & launch status
│   │   │   └── status_bar.py     # Detected environment tools & Antigravity status
│   │   └── dialogs/
│   │       ├── health_check_modal.py    # Pre-flight health audit dialog
│   │       ├── ide_selection_modal.py   # IDE selection dialog with 'Remember' preference
│   │       ├── project_editor.py        # Project modal with dedicated Resources management tab
│   │       ├── resource_editor_modal.py # Add/Edit resource modal dialog
│   │       └── settings_dialog.py       # Global preferences & Windows autostart
│   └── utils/
│       └── logger.py             # Thread-safe logging with subscriber UI streaming
├── tests/                        # 48 automated unit, integration, and acceptance tests
│   ├── test_antigravity.py
│   ├── test_detector.py
│   ├── test_e2e_workflow.py
│   ├── test_ide_selection.py
│   ├── test_models.py
│   ├── test_orchestrator.py
│   ├── test_resources_workspace.py # 9 acceptance criteria for multi-resource launcher
│   ├── test_security.py
│   ├── test_storage.py
│   ├── test_terminal.py
│   └── test_ui_launch.py
├── devpilot.bat              # Windows batch launcher
├── main.py                   # Application entry point
├── requirements.txt          # Python package dependencies
└── README.md                 # Documentation
```

---

## 🛠️ Requirements & Setup

### Prerequisites
- Windows 10 / 11
- Python 3.10+ (Python 3.12 verified)
- Google Antigravity IDE (detected at `%LOCALAPPDATA%\Programs\Antigravity IDE\`)

### Install Dependencies
```powershell
cd E:\DevPilot
pip install -r requirements.txt
```

---

## ▶️ Running DevPilot

### Option 1: Double-click Batch Launcher
Double-click `devpilot.bat` or run:
```powershell
.\devpilot.bat
```

### Option 2: Python Command
```powershell
python main.py
```

---

## 🧪 Automated Tests

DevPilot includes a complete test suite covering models, persistence, security redaction, terminal builders, Antigravity CLI args, and workflow orchestration.

Run all tests:
```powershell
python -m unittest discover -s tests -p "test_*.py"
```
*(All 34 tests pass with 0 failures.)*

---

## 🔍 Antigravity Integration Notes & Limitations
1. **Window Reuse**: DevPilot uses `antigravity-ide.cmd -r "<path>"` to reuse existing windows or focus the active instance.
2. **Process Detection**: DevPilot monitors `Antigravity IDE.exe` and `Antigravity.exe` using `psutil`.
3. **Session Restoration Boundary**: DevPilot reopens the project root folder and any specified initial files. Agent conversation threads inside Antigravity are managed internally by Antigravity's own state engine; DevPilot does not fabricate mock chat histories.

