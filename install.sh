#!/usr/bin/env bash
# Testoria one-shot installer.
#
#   curl -fsSL https://raw.githubusercontent.com/Testoria-Framework/testoria/main/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/Testoria-Framework/testoria/main/install.sh | bash -s -- --all
#   ./install.sh --python --javascript --java --verify
#
# Works on macOS, Linux and Windows (Git Bash / MSYS2 / WSL). Run ./install.sh --help for all options.
set -euo pipefail

REPO_URL="${TESTORIA_REPO:-https://github.com/Testoria-Framework/testoria.git}"
BRANCH="${TESTORIA_BRANCH:-main}"
DEFAULT_DIR="${TESTORIA_HOME:-$HOME/.testoria}"

INSTALL_DIR=""
BIN_DIR="${TESTORIA_BIN_DIR:-$HOME/.local/bin}"
WITH_JS=false
WITH_JAVA=false
WITH_PERF=false
WITH_DOCKER=false
INSTALL_SYSTEM_DEPS=false
VERIFY=false
INIT_DIR=""
UPDATE_PATH=true
UNINSTALL=false
ASSUME_YES=false
QUIET=false
PYTHON_BIN="${PYTHON:-}"

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  B=$'\033[1m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; C=$'\033[36m'; D=$'\033[2m'; N=$'\033[0m'
else
  B=""; G=""; Y=""; R=""; C=""; D=""; N=""
fi
say()  { [ "$QUIET" = true ] || printf '%s\n' "$*"; }
step() { say "${C}==>${N} ${B}$*${N}"; }
ok()   { say "  ${G}✔${N} $*"; }
warn() { printf '  %s!%s %s\n' "$Y" "$N" "$*" >&2; }
die()  { printf '%sError:%s %s\n' "$R" "$N" "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

usage() {
  cat <<USAGE
${B}Testoria installer${N}

Usage: install.sh [options]

Components (the Python CLI is always installed):
  --javascript, --js     install Node.js dependencies for the JavaScript suites
  --java                 prepare Java/Maven (downloads deps through ./mvnw)
  --perf                 install load-testing extras (locust; k6 via package manager if --system-deps)
  --docker               build the 'testoria' Docker image
  --all                  everything above

Options:
  --dir DIR              install location (default: inside the current checkout, else $DEFAULT_DIR)
  --bin-dir DIR          where the 'testoria' launcher goes (default: $BIN_DIR)
  --branch NAME          git branch to install when cloning (default: $BRANCH)
  --python PATH          Python interpreter to use (default: python3 / python / py -3)
  --system-deps          use brew/apt/dnf/pacman/winget/choco to install missing Python, Node, Java, git
  --no-path              do not edit shell profiles to add the launcher to PATH
  --init DIR             scaffold a starter project in DIR after installing
  --verify               run the self-test (all suites against the bundled demo API)
  -y, --yes              do not ask for confirmation before system package installs
  -q, --quiet            less output
  --uninstall            remove the virtualenv and launcher (keeps the checkout)
  -h, --help             show this help

Examples:
  ./install.sh                            # CLI only
  ./install.sh --all --verify             # every language + Docker, then self-test
  ./install.sh --js --init ~/my-api-tests # CLI + JS deps, create a starter project
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --javascript|--js) WITH_JS=true ;;
    --java) WITH_JAVA=true ;;
    --perf|--performance) WITH_PERF=true ;;
    --docker) WITH_DOCKER=true ;;
    --all) WITH_JS=true; WITH_JAVA=true; WITH_PERF=true; WITH_DOCKER=true ;;
    --dir) INSTALL_DIR="${2:?--dir needs a value}"; shift ;;
    --bin-dir) BIN_DIR="${2:?--bin-dir needs a value}"; shift ;;
    --branch) BRANCH="${2:?--branch needs a value}"; shift ;;
    --python) PYTHON_BIN="${2:?--python needs a value}"; shift ;;
    --system-deps) INSTALL_SYSTEM_DEPS=true ;;
    --no-path) UPDATE_PATH=false ;;
    --init) INIT_DIR="${2:?--init needs a directory}"; shift ;;
    --verify|--test) VERIFY=true ;;
    -y|--yes) ASSUME_YES=true ;;
    -q|--quiet) QUIET=true ;;
    --uninstall) UNINSTALL=true ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1 (see --help)" ;;
  esac
  shift
done

# --------------------------------------------------------------------------- platform
OS="$(uname -s 2>/dev/null || echo unknown)"
case "$OS" in
  Darwin) PLATFORM=macos ;;
  Linux) if grep -qi microsoft /proc/version 2>/dev/null; then PLATFORM=wsl; else PLATFORM=linux; fi ;;
  MINGW*|MSYS*|CYGWIN*) PLATFORM=windows ;;
  *) PLATFORM=unknown ;;
esac

PKG=""
if   have brew;   then PKG=brew
elif have apt-get; then PKG=apt
elif have dnf;    then PKG=dnf
elif have yum;    then PKG=yum
elif have pacman; then PKG=pacman
elif have apk;    then PKG=apk
elif have zypper; then PKG=zypper
elif have winget; then PKG=winget
elif have choco;  then PKG=choco
fi

SUDO=""
if [ "$(id -u 2>/dev/null || echo 1)" != "0" ] && have sudo; then SUDO="sudo"; fi

pkg_install() {  # pkg_install <generic-name>
  local name="$1" pkgname="$1"
  [ -n "$PKG" ] || { warn "No supported package manager found; install $name manually."; return 1; }
  if [ "$ASSUME_YES" != true ] && [ -t 0 ]; then
    printf '  Install %s with %s? [Y/n] ' "$name" "$PKG"; read -r ans
    case "$ans" in [nN]*) return 1 ;; esac
  fi
  case "$PKG:$name" in
    brew:python) pkgname=python@3.12 ;; brew:java) pkgname=openjdk@17 ;;
    apt:python|yum:python|dnf:python|zypper:python) pkgname="python3 python3-venv python3-pip" ;;
    apk:python) pkgname="python3 py3-pip" ;; pacman:python) pkgname="python python-pip" ;;
    apt:node) pkgname="nodejs npm" ;; dnf:node|yum:node|zypper:node|apk:node) pkgname="nodejs npm" ;; pacman:node) pkgname="nodejs npm" ;;
    apt:java) pkgname=openjdk-17-jdk ;; dnf:java|yum:java) pkgname=java-17-openjdk-devel ;; pacman:java) pkgname=jdk17-openjdk ;;
    apk:java) pkgname=openjdk17 ;; zypper:java) pkgname=java-17-openjdk-devel ;;
    winget:python) pkgname=Python.Python.3.12 ;; winget:node) pkgname=OpenJS.NodeJS.LTS ;; winget:java) pkgname=EclipseAdoptium.Temurin.17.JDK ;;
    winget:git) pkgname=Git.Git ;; winget:k6) pkgname=k6.k6 ;;
    choco:python) pkgname=python ;; choco:node) pkgname=nodejs-lts ;; choco:java) pkgname=temurin17 ;;
    brew:node) pkgname=node ;;
  esac
  step "Installing $name via $PKG"
  # shellcheck disable=SC2086
  case "$PKG" in
    brew) brew install $pkgname ;;
    apt) $SUDO apt-get update -qq && $SUDO apt-get install -y -qq $pkgname ;;
    dnf) $SUDO dnf install -y -q $pkgname ;;
    yum) $SUDO yum install -y -q $pkgname ;;
    pacman) $SUDO pacman -S --noconfirm --needed $pkgname ;;
    apk) $SUDO apk add --no-cache $pkgname ;;
    zypper) $SUDO zypper -n install $pkgname ;;
    winget) winget install -e --silent --accept-package-agreements --accept-source-agreements --id $pkgname ;;
    choco) choco install -y $pkgname ;;
  esac
}

# --------------------------------------------------------------------------- python
find_python() {
  local c
  for c in "$PYTHON_BIN" python3 python "py -3"; do
    [ -n "$c" ] || continue
    # shellcheck disable=SC2086
    if $c -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1; then
      PYTHON_BIN="$c"; return 0
    fi
  done
  return 1
}

# --------------------------------------------------------------------------- source
locate_source() {
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
  if [ -z "$INSTALL_DIR" ] && [ -n "$here" ] && [ -f "$here/testoria/cli.py" ]; then
    INSTALL_DIR="$here"; return
  fi
  INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_DIR}"
  if [ -f "$INSTALL_DIR/testoria/cli.py" ]; then
    if [ -d "$INSTALL_DIR/.git" ] && have git; then
      step "Updating $INSTALL_DIR"
      git -C "$INSTALL_DIR" pull --ff-only --quiet || warn "git pull failed; using existing checkout"
    fi
    return
  fi
  have git || { [ "$INSTALL_SYSTEM_DEPS" = true ] && pkg_install git; } || die "git is required (or use --system-deps)"
  step "Cloning $REPO_URL ($BRANCH) into $INSTALL_DIR"
  git clone --depth 1 --branch "$BRANCH" --quiet "$REPO_URL" "$INSTALL_DIR"
}

venv_python() {
  if [ -x "$INSTALL_DIR/.venv/bin/python" ]; then echo "$INSTALL_DIR/.venv/bin/python"
  else echo "$INSTALL_DIR/.venv/Scripts/python.exe"; fi
}

# --------------------------------------------------------------------------- launcher
write_launcher() {
  mkdir -p "$BIN_DIR"
  local vpy; vpy="$(venv_python)"
  cat > "$BIN_DIR/testoria" <<LAUNCH
#!/usr/bin/env bash
# Generated by Testoria install.sh
export PYTHONPATH="$INSTALL_DIR\${PYTHONPATH:+:\$PYTHONPATH}"
exec "$vpy" -m testoria "\$@"
LAUNCH
  chmod +x "$BIN_DIR/testoria"
  if [ "$PLATFORM" = windows ]; then
    local winpy windir
    winpy="$(cygpath -w "$vpy" 2>/dev/null || echo "$vpy")"
    windir="$(cygpath -w "$INSTALL_DIR" 2>/dev/null || echo "$INSTALL_DIR")"
    printf '@echo off\r\nset "PYTHONPATH=%s;%%PYTHONPATH%%"\r\n"%s" -m testoria %%*\r\n' "$windir" "$winpy" > "$BIN_DIR/testoria.cmd"
  fi
  ok "launcher: $BIN_DIR/testoria"
}

add_to_path() {
  case ":$PATH:" in *":$BIN_DIR:"*) return ;; esac
  [ "$UPDATE_PATH" = true ] || { warn "Add $BIN_DIR to your PATH to use 'testoria'"; return; }
  local line="export PATH=\"$BIN_DIR:\$PATH\"" f added=false
  for f in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.profile"; do
    [ -f "$f" ] || continue
    grep -qsF "$BIN_DIR" "$f" && { added=true; continue; }
    printf '\n# Added by Testoria installer\n%s\n' "$line" >> "$f"; added=true
    ok "added $BIN_DIR to PATH in $f"
  done
  if [ "$added" = false ]; then
    printf '\n# Added by Testoria installer\n%s\n' "$line" >> "$HOME/.profile"; ok "added $BIN_DIR to PATH in ~/.profile"
  fi
  if have fish && [ -d "$HOME/.config/fish" ]; then
    mkdir -p "$HOME/.config/fish/conf.d"
    echo "fish_add_path -g $BIN_DIR" > "$HOME/.config/fish/conf.d/testoria.fish"
  fi
  NEED_RELOAD=true
}

# --------------------------------------------------------------------------- uninstall
if [ "$UNINSTALL" = true ]; then
  locate_source
  step "Uninstalling Testoria"
  rm -rf "$INSTALL_DIR/.venv" && ok "removed $INSTALL_DIR/.venv"
  rm -f "$BIN_DIR/testoria" "$BIN_DIR/testoria.cmd" && ok "removed launcher from $BIN_DIR"
  say "The checkout at $INSTALL_DIR and PATH lines in your shell profile were left in place."
  exit 0
fi

# --------------------------------------------------------------------------- main
say "${B}Testoria installer${N} ${D}(platform: $PLATFORM, package manager: ${PKG:-none})${N}"

step "Checking Python"
if ! find_python; then
  [ "$INSTALL_SYSTEM_DEPS" = true ] && pkg_install python && hash -r && find_python \
    || die "Python 3.8+ not found. Install it (https://python.org) or re-run with --system-deps"
fi
ok "$($PYTHON_BIN --version 2>&1) ($PYTHON_BIN)"

locate_source
cd "$INSTALL_DIR"
ok "source: $INSTALL_DIR"

step "Creating virtualenv"
if [ ! -x "$(venv_python)" ]; then
  # shellcheck disable=SC2086
  $PYTHON_BIN -m venv "$INSTALL_DIR/.venv" 2>/dev/null || {
    [ "$PKG" = apt ] && [ "$INSTALL_SYSTEM_DEPS" = true ] && pkg_install python && $PYTHON_BIN -m venv "$INSTALL_DIR/.venv"
  } || die "Could not create a virtualenv. On Debian/Ubuntu install python3-venv (or use --system-deps)."
fi
VPY="$(venv_python)"
"$VPY" -m pip install --quiet --disable-pip-version-check --upgrade pip
"$VPY" -m pip install --quiet --disable-pip-version-check -r requirements.txt
ok "Python dependencies installed"
if [ "$WITH_PERF" = true ]; then
  "$VPY" -m pip install --quiet --disable-pip-version-check -r requirements-perf.txt && ok "locust installed"
  if ! have k6; then
    if [ "$INSTALL_SYSTEM_DEPS" = true ] && [ -n "$PKG" ] && [ "$PKG" != apt ]; then pkg_install k6 || true
    else warn "k6 not found (optional): https://k6.io/docs/get-started/installation/"; fi
  fi
fi

step "Installing the testoria command"
write_launcher
NEED_RELOAD=false
add_to_path

if [ "$WITH_JS" = true ]; then
  step "JavaScript suites"
  if ! have node || ! have npm; then
    [ "$INSTALL_SYSTEM_DEPS" = true ] && pkg_install node && hash -r || true
  fi
  if have npm; then
    if [ -f package-lock.json ]; then npm ci --no-audit --no-fund --loglevel=error; else npm install --no-audit --no-fund --loglevel=error; fi
    ok "Node $(node --version) dependencies installed"
  else
    warn "Node.js 18+ not found; skipped (use --system-deps or install from https://nodejs.org)"
  fi
fi

if [ "$WITH_JAVA" = true ]; then
  step "Java suites"
  if ! have java; then
    [ "$INSTALL_SYSTEM_DEPS" = true ] && pkg_install java && hash -r || true
  fi
  if have java; then
    chmod +x mvnw 2>/dev/null || true
    if ./mvnw -q -B -DskipTests test-compile; then ok "Java $(java -version 2>&1 | head -1 | cut -d'"' -f2) and Maven dependencies ready"
    else warn "Maven build failed; see output above"; fi
  else
    warn "JDK 17+ not found; skipped (use --system-deps or install Temurin from https://adoptium.net)"
  fi
fi

if [ "$WITH_DOCKER" = true ]; then
  step "Docker image"
  if have docker && docker info >/dev/null 2>&1; then
    docker build -q -t testoria:latest . >/dev/null && ok "built image testoria:latest (docker run --rm -v \"\$PWD:/work\" testoria run)"
  else
    warn "Docker is not installed or not running; skipped"
  fi
fi

if [ -n "$INIT_DIR" ]; then
  step "Scaffolding project in $INIT_DIR"
  "$BIN_DIR/testoria" init "$INIT_DIR"
fi

if [ "$VERIFY" = true ]; then
  step "Self-test"
  langs="python"
  [ "$WITH_JS" = true ] && have npm && langs="$langs,javascript"
  [ "$WITH_JAVA" = true ] && have java && langs="$langs,java"
  bash scripts/run_tests.sh --language "$langs" --type all
fi

say ""
say "${G}${B}Testoria is installed.${N}"
"$BIN_DIR/testoria" --version
say ""
say "  testoria doctor                 check optional tools"
say "  testoria init my-tests          create a starter project"
say "  testoria run --mock             run specs against the built-in mock API"
say "  testoria demo-api               start the sample REST API on :8080"
say "  testoria --help                 all commands"
if [ "${NEED_RELOAD:-false}" = true ]; then
  say ""
  say "${Y}Open a new terminal (or run: export PATH=\"$BIN_DIR:\$PATH\") to use 'testoria'.${N}"
fi
