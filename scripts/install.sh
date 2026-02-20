#!/bin/bash
# AI Orchestrator - One-command install (curl ... | bash)
# Usage: curl -sSL https://raw.githubusercontent.com/YOUR_REPO/main/scripts/install.sh | bash
# Or: git clone https://github.com/YOUR_REPO/ai-orchestrator.git && cd ai-orchestrator && ./scripts/setup.sh
set -e
REPO_URL="${REPO_URL:-https://github.com/your-org/ai-orchestrator.git}"
TARGET="${TARGET:-./ai-orchestrator}"
echo "Installing AI Orchestrator to $TARGET"
if [ -d "$TARGET" ]; then
  echo "Directory exists. Running setup..."
  cd "$TARGET"
  ./scripts/setup.sh
else
  git clone "$REPO_URL" "$TARGET"
  cd "$TARGET"
  ./scripts/setup.sh
fi
echo "Done. cd $TARGET && python main.py"
