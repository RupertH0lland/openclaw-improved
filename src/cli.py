"""CLI - all configuration and onboarding via command line. No .env required."""
import argparse
import getpass
import sys
import webbrowser
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "config"
SETTINGS_PATH = CONFIG_DIR / "settings.yaml"
MODELS_PATH = CONFIG_DIR / "models.yaml"
DEFAULT_PREFIX = "ai"


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return {}
    with open(SETTINGS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_settings(data: dict) -> None:
    _ensure_config_dir()
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def _load_models() -> dict:
    if not MODELS_PATH.exists():
        return {"routing": {"default": "gpt-4o-mini"}, "ollama": {"enabled": False, "base_url": "http://localhost:11434", "models": []}}
    with open(MODELS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_models(data: dict) -> None:
    _ensure_config_dir()
    with open(MODELS_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def _prompt(prompt: str, default: str = "", secret: bool = False) -> str:
    if default:
        p = f"{prompt} [{default}]: "
    else:
        p = f"{prompt}: "
    if secret:
        v = getpass.getpass(p)
    else:
        v = input(p).strip()
    return v if v else default


def _prompt_yes(prompt: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    v = input(f"{prompt} [{d}]: ").strip().lower()
    if not v:
        return default
    return v in ("y", "yes")


def cmd_setup(prefix: str) -> None:
    """Interactive onboarding - configure everything via CLI. Launches browser when ready."""
    print(f"\n{prefix} Orchestrator - Setup\n")
    _ensure_config_dir()

    settings = _load_settings()
    models = _load_models()

    # Data paths
    settings.setdefault("data_dir", "./data")
    settings.setdefault("output_dir", "./data/output")
    settings["data_dir"] = _prompt("Data directory", settings["data_dir"])
    settings["output_dir"] = _prompt("Output directory", settings["output_dir"])

    # API keys (stored in config - no .env)
    if "secrets" not in settings:
        settings["secrets"] = {}
    print("\n--- API Keys (press Enter to skip) ---")
    settings["secrets"]["openai_api_key"] = _prompt("OpenAI API key", settings["secrets"].get("openai_api_key", ""), secret=True)
    settings["secrets"]["anthropic_api_key"] = _prompt("Anthropic API key", settings["secrets"].get("anthropic_api_key", ""), secret=True)

    # Dashboard
    settings.setdefault("dashboard", {})
    settings["dashboard"]["enabled"] = True
    settings["dashboard"]["host"] = _prompt("Dashboard host", settings["dashboard"].get("host", "127.0.0.1"))
    settings["dashboard"]["port"] = int(_prompt("Dashboard port", str(settings["dashboard"].get("port", 8000))))
    pwd = _prompt("Dashboard password (optional, press Enter for none)", "", secret=True)
    if pwd:
        try:
            from passlib.context import CryptContext
            settings["dashboard"]["password_hash"] = CryptContext(schemes=["bcrypt"]).hash(pwd)
        except ImportError:
            settings["dashboard"]["password_hash"] = ""
            print("  (install passlib for password hashing)")
    else:
        settings["dashboard"]["password_hash"] = ""

    # Telegram
    settings.setdefault("telegram", {})
    settings["telegram"]["enabled"] = _prompt_yes("Enable Telegram bot?", False)
    if settings["telegram"]["enabled"]:
        settings["secrets"]["telegram_bot_token"] = _prompt("Telegram bot token", settings["secrets"].get("telegram_bot_token", ""), secret=True)
        settings["telegram"]["bot_token"] = ""  # Uses secrets
    else:
        settings["telegram"]["bot_token"] = ""

    # Sub-agents, Ollama
    settings["use_subagents"] = _prompt_yes("Enable sub-agents?", False)
    models.setdefault("ollama", {})
    models["ollama"]["enabled"] = _prompt_yes("Enable Ollama (local models)?", False)
    if models["ollama"]["enabled"]:
        models["ollama"]["base_url"] = _prompt("Ollama URL", models["ollama"].get("base_url", "http://localhost:11434"))

    # Budget, resource limits
    settings.setdefault("budget", {})
    settings["budget"]["enabled"] = _prompt_yes("Enable budget caps?", False)
    if settings["budget"]["enabled"]:
        settings["budget"]["daily_usd"] = float(_prompt("Daily USD limit", str(settings["budget"].get("daily_usd", 10))))
    settings.setdefault("resource_limits", {})
    settings["resource_limits"]["enabled"] = _prompt_yes("Enable resource limits?", False)

    # Command prefix
    settings["cli_prefix"] = _prompt("Command line prefix", settings.get("cli_prefix", DEFAULT_PREFIX))

    _save_settings(settings)
    _save_models(models)
    print("\nConfiguration saved.\n")

    # Auto-start
    if _prompt_yes("Start with computer (auto-start on boot)?", False):
        _install_autostart(prefix)

    # Run and launch browser when ready
    print("\nStarting orchestrator...")
    _save_settings(settings)  # in case autostart modified
    url = f"http://{settings['dashboard']['host']}:{settings['dashboard']['port']}"
    print(f"Dashboard: {url}")

    import threading
    def open_browser():
        import time
        time.sleep(2.5)
        webbrowser.open(url)
    threading.Thread(target=open_browser, daemon=True).start()
    _run_server()


def _install_autostart(prefix: str) -> None:
    """Install auto-start (systemd on Linux, Task Scheduler on Windows)."""
    import platform
    import subprocess
    if platform.system() == "Windows":
        script = ROOT / "scripts" / "install_autostart.ps1"
        try:
            subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                cwd=str(ROOT), check=False
            )
            print("  Auto-start installed (Task Scheduler)")
        except Exception:
            print(f"  Run manually: powershell -ExecutionPolicy Bypass -File {script}")
    else:
        script = ROOT / "scripts" / "install_autostart.sh"
        try:
            subprocess.run(["sudo", "bash", str(script)], cwd=str(ROOT), check=False)
            print("  Auto-start installed (systemd)")
        except Exception:
            print(f"  Run: sudo bash {script}")


def _run_server() -> None:
    """Start the dashboard server."""
    import os
    os.chdir(ROOT)
    settings = _load_settings()
    host = settings.get("dashboard", {}).get("host", "127.0.0.1")
    port = settings.get("dashboard", {}).get("port", 8000)
    import uvicorn
    from src.dashboard.app import app
    uvicorn.run(app, host=host, port=port)


def cmd_run() -> None:
    """Run the orchestrator (no browser launch)."""
    import os
    os.chdir(ROOT)
    settings = _load_settings()
    if not SETTINGS_PATH.exists():
        print("Run setup first: python main.py setup")
        sys.exit(1)
    host = settings.get("dashboard", {}).get("host", "127.0.0.1")
    port = settings.get("dashboard", {}).get("port", 8000)
    import uvicorn
    from src.dashboard.app import app
    uvicorn.run(app, host=host, port=port)


def cmd_config_get(key: str) -> None:
    """Get config value."""
    settings = _load_settings()
    keys = key.split(".")
    v = settings
    for k in keys:
        if isinstance(v, dict):
            v = v.get(k, "")
        else:
            v = ""
            break
    print(v)


def cmd_config_set(key: str, value: str) -> None:
    """Set config value."""
    settings = _load_settings()
    keys = key.split(".")
    d = settings
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    try:
        val = int(value)
    except ValueError:
        try:
            val = float(value)
        except ValueError:
            val = value
    d[keys[-1]] = val
    _save_settings(settings)
    print(f"Set {key} = {value}")


def cmd_shell(prefix: str) -> None:
    """Interactive shell with custom prefix."""
    settings = _load_settings()
    p = settings.get("cli_prefix", prefix) or DEFAULT_PREFIX
    prompt = f"{p}> "
    print(f"Type 'help' for commands. Prefix: {p}\n")
    while True:
        try:
            line = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()
        if cmd == "help":
            print("  setup     - Run setup/onboarding")
            print("  run       - Start orchestrator")
            print("  config get <key>  - Get config")
            print("  config set <key> <value>  - Set config")
            print("  exit      - Exit shell")
        elif cmd == "setup":
            cmd_setup(p)
        elif cmd == "run":
            cmd_run()
        elif cmd == "config" and len(parts) >= 3:
            if parts[1] == "get":
                cmd_config_get(parts[2])
            elif parts[1] == "set" and len(parts) >= 4:
                cmd_config_set(parts[2], " ".join(parts[3:]))
        elif cmd in ("exit", "quit"):
            break


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai", description="AI Orchestrator CLI")
    parser.add_argument("--prefix", "-p", default=None, help="Command prefix (overrides config)")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("setup", help="Interactive setup and onboarding")
    sub.add_parser("run", help="Run the orchestrator")
    sub.add_parser("shell", help="Interactive shell with custom prefix")
    cfg = sub.add_parser("config", help="Get/set config")
    cfg.add_argument("action", choices=["get", "set"])
    cfg.add_argument("key")
    cfg.add_argument("value", nargs="*", default=[])

    args = parser.parse_args()
    prefix = args.prefix
    if prefix is None:
        s = _load_settings()
        prefix = s.get("cli_prefix", DEFAULT_PREFIX)

    if args.cmd == "setup":
        cmd_setup(prefix)
    elif args.cmd == "run":
        cmd_run()
    elif args.cmd == "shell":
        cmd_shell(prefix)
    elif args.cmd == "config":
        if args.action == "get":
            cmd_config_get(args.key)
        else:
            val = " ".join(args.value) if args.value else ""
            if not val:
                print("config set requires a value")
                sys.exit(1)
            cmd_config_set(args.key, val)
    else:
        # Default: run setup if no config, else run
        if not SETTINGS_PATH.exists():
            print("No config found. Running setup...")
            cmd_setup(prefix)
        else:
            cmd_run()


if __name__ == "__main__":
    main()
