#!/usr/bin/env bash
# Idempotent toolchain setup for a fresh cloud container. Safe to re-run; skips what exists.
# Called by the SessionStart hook in .claude/settings.json and by hand: shorts-editor/setup.sh
set -uo pipefail
HF_VERSION=0.8.202
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }

echo "shorts-editor setup"
command -v ffmpeg >/dev/null && ok "ffmpeg $(ffmpeg -version | head -1 | cut -d' ' -f3)" || warn "ffmpeg missing (apt-get install ffmpeg)"

if [ "$(hyperframes --version 2>/dev/null | grep -o '[0-9.]*' | head -1)" != "$HF_VERSION" ]; then
  npm i -g "hyperframes@$HF_VERSION" >/dev/null 2>&1 && ok "hyperframes $HF_VERSION installed" || warn "hyperframes install failed"
else ok "hyperframes $HF_VERSION"; fi
hyperframes telemetry disable >/dev/null 2>&1 || true
[ -d "$HOME/.claude/skills/hyperframes" ] || hyperframes skills >/dev/null 2>&1
[ -d "$HOME/.claude/skills/hyperframes" ] && ok "hyperframes agent skills" || warn "hyperframes skills not installed"
hyperframes browser path >/dev/null 2>&1 || hyperframes browser ensure >/dev/null 2>&1
hyperframes browser path >/dev/null 2>&1 && ok "render browser" || warn "chrome-headless-shell missing (hyperframes browser ensure)"

python3 -c "import faster_whisper" 2>/dev/null || pip install -q --break-system-packages faster-whisper >/dev/null 2>&1
python3 -c "import faster_whisper" 2>/dev/null && ok "faster-whisper (fallback ASR)" || warn "faster-whisper not installed"
command -v git-lfs >/dev/null && git lfs install --skip-repo >/dev/null 2>&1 && ok "git-lfs"

# Credentials and network (report only; never print secret values)
[ -n "${ELEVENLABS_API_KEY:-}" ] && ok "ELEVENLABS_API_KEY set" || warn "ELEVENLABS_API_KEY not set -> transcription falls back to Whisper"
probe() { curl -s -o /dev/null -m 6 -w '%{http_code}' "https://$1/" 2>/dev/null; }
for h in api.elevenlabs.io huggingface.co www.myinstants.com pixabay.com cdn.pixabay.com www.googleapis.com; do
  c=$(probe "$h"); [ "$c" != "000" ] && ok "network: $h" || warn "network: $h blocked (add to environment Allowed domains)"
done
exit 0
