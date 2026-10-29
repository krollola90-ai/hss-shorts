#!/usr/bin/env bash
# Idempotent toolchain setup for a fresh cloud session. Safe to re-run; skips what exists.
#   shorts-editor/setup.sh            (also run by the SessionStart hook in .claude/settings.json)
# Writes shorts-editor/.env.sh with the variables the pipeline needs; `shorts` sources it.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HF_VERSION=0.8.202
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }

# The cloud proxy exempts registry.npmjs.org / pypi.org via NO_PROXY, but direct DNS to them is
# blocked, so package managers must go THROUGH the proxy: clear the no-proxy lists for installs.
pm() { NO_PROXY= no_proxy= npm_config_noproxy= "$@"; }

echo "shorts-editor setup"
command -v ffmpeg >/dev/null && ok "ffmpeg $(ffmpeg -version | head -1 | cut -d' ' -f3)" || warn "ffmpeg missing (apt-get install ffmpeg)"

if [ "$(hyperframes --version 2>/dev/null | grep -o '[0-9.]*' | head -1)" != "$HF_VERSION" ]; then
  pm npm i -g "hyperframes@$HF_VERSION" >/dev/null 2>&1 && ok "hyperframes $HF_VERSION installed" || warn "hyperframes install failed"
else ok "hyperframes $HF_VERSION"; fi
hyperframes telemetry disable >/dev/null 2>&1 || true
[ -d "$HOME/.claude/skills/hyperframes" ] || pm hyperframes skills >/dev/null 2>&1
[ -d "$HOME/.claude/skills/hyperframes" ] && ok "hyperframes agent skills" || warn "hyperframes skills not installed"

# Render browser: hyperframes' own chrome-headless-shell if it can be fetched, else the
# Playwright Chromium that ships with the cloud image.
BROWSER=""
hyperframes browser path >/dev/null 2>&1 || pm hyperframes browser ensure >/dev/null 2>&1
if hyperframes browser path >/dev/null 2>&1; then BROWSER="$(hyperframes browser path 2>/dev/null | tail -1)"
else BROWSER="$(ls -d /opt/pw-browsers/chromium-*/chrome-linux*/chrome 2>/dev/null | tail -1)"; fi
[ -n "$BROWSER" ] && ok "render browser: $BROWSER" || warn "no render browser (hyperframes browser ensure)"

python3 -c "import faster_whisper" 2>/dev/null || pm pip install -q --break-system-packages faster-whisper >/dev/null 2>&1
python3 -c "import faster_whisper" 2>/dev/null && ok "faster-whisper (free transcription)" || warn "faster-whisper not installed"
command -v git-lfs >/dev/null && git lfs install --skip-repo >/dev/null 2>&1 && ok "git-lfs"

cat > "$HERE/.env.sh" <<EOF
export HYPERFRAMES_BROWSER_PATH="$BROWSER"
export NO_PROXY= no_proxy= npm_config_noproxy=
EOF
ok "env -> shorts-editor/.env.sh"

# Transcription route (report only; never print secret values)
[ -n "${ELEVENLABS_API_KEY:-}" ] && ok "ELEVENLABS_API_KEY set (Scribe REST)" \
  || ok "transcription: ElevenLabs connector (shorts import-scribe) or Whisper medium (free)"
probe() { curl -s -o /dev/null -m 6 -w '%{http_code}' "https://$1/" 2>/dev/null; }
for h in api.elevenlabs.io huggingface.co drive.usercontent.google.com storage.googleapis.com; do
  c=$(probe "$h"); [ "$c" != "000" ] && ok "network: $h" || warn "network: $h blocked (add to environment Allowed domains)"
done
exit 0
