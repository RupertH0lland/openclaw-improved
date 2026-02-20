# AI Orchestrator

A generic, packageable AI orchestrator with Telegram interface, local dashboard, cost-optimized sub-agents, and full device access. Config-driven and portable across PC, Raspberry Pi 5, and laptop.

## Quick Start

Download, run one command, complete onboarding in the CLI. No .env files.

### Linux / macOS

```bash
git clone https://github.com/your-org/ai-orchestrator.git
cd ai-orchestrator
./scripts/setup.sh
```

First run: interactive onboarding (API keys, dashboard, etc.) → browser opens when ready.  
Later runs: starts immediately.

### Windows

```powershell
git clone https://github.com/your-org/ai-orchestrator.git
cd ai-orchestrator
.\scripts\setup.ps1
```

Same flow: first run = onboarding, then ready. Reconfigure anytime with `python main.py setup`.

### CLI Commands

- `python main.py setup` - Interactive onboarding (API keys, dashboard, Telegram, etc.)
- `python main.py run` - Start orchestrator
- `python main.py shell` - Interactive shell with custom prefix
- `python main.py config get <key>` / `config set <key> <value>` - Get/set config
- `--prefix` - Custom command prefix (e.g. `python main.py --prefix orch run`)

### Auto-start with computer

During setup, choose "Start with computer". Or run:
- Windows: `powershell -ExecutionPolicy Bypass -File scripts/install_autostart.ps1`
- Linux: `sudo bash scripts/install_autostart.sh`

## Configuration

All config stored in `config/settings.yaml` (written by CLI). API keys in `config/settings.yaml` under `secrets`.

## Deployment Scenarios

### Single PC
Run on your main machine. Set `dashboard.host: 0.0.0.0` to access from other devices on the same network.

### Raspberry Pi 5 (8GB)
Same setup. Sub-agents use cloud APIs (no local inference). Optionally enable Ollama on a separate PC and set `ollama.base_url` to the PC's Tailscale IP.

### Pi 5 + Remote Ollama
1. Run Ollama on your PC
2. Join both to Tailscale
3. In `models.yaml`: `ollama.enabled: true`, `ollama.base_url: http://<pc-tailscale-ip>:11434`

### Cloud-only
No Ollama. Set `ollama.enabled: false`. All inference via OpenAI/Anthropic.

## Features

- **Dashboard**: Chat, agent monitor, file browser, health, cost tracking
- **Telegram**: Optional bot for remote chat
- **Sub-agents**: Enable `use_subagents: true` for task routing
- **Cost optimization**: Response cache, budget caps, token tracking
- **Memory**: Chroma + SQLite for context
- **Browser automation**: Screenshots (Playwright)
- **CRON**: Manage scheduled jobs (Unix only)

## Remote Access

- **Tailscale**: Join devices to a VPN, access dashboard at `http://<host-ip>:8000`
- **Cloudflare Tunnel**: Expose via `cloudflared tunnel` for HTTPS
