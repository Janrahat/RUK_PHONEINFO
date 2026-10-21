#!/data/data/com.termux/files/usr/bin/bash
#
# RUK_PHONEINFO installer for Termux (Android) and any Linux shell.
#
#   bash install.sh              # full install (asks before optional tools)
#   bash install.sh --no-deps    # skip optional package installation
#   bash install.sh --prefix DIR # install into DIR instead of ~/.local
#
set -euo pipefail

APP_NAME="RUK_PHONEINFO"
APP_SLUG="ruk_phoneinfo"
VERSION="1.0.0"

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${HOME}/.local"
INSTALL_DEPS=1

while [ $# -gt 0 ]; do
  case "$1" in
    --no-deps) INSTALL_DEPS=0 ;;
    --prefix) shift; PREFIX="${1:-$PREFIX}" ;;
    -h|--help)
      sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

BIN_DIR="${PREFIX}/bin"
LIB_DIR="${PREFIX}/lib/${APP_SLUG}"

c_reset='\033[0m'; c_cyan='\033[38;5;80m'; c_green='\033[38;5;114m'
c_yellow='\033[38;5;221m'; c_red='\033[38;5;203m'; c_grey='\033[38;5;245m'

say()  { printf '%b\n' "${c_cyan}[*]${c_reset} $*"; }
ok()   { printf '%b\n' "${c_green}[+]${c_reset} $*"; }
warn() { printf '%b\n' "${c_yellow}[!]${c_reset} $*"; }
fail() { printf '%b\n' "${c_red}[-]${c_reset} $*" >&2; exit 1; }

printf '%b\n' "${c_cyan}"
cat <<'BANNER'
  ██████╗ ██╗   ██╗██╗  ██╗    ██████╗ ██╗  ██╗ ██████╗ ███╗   ██╗███████╗
  ██╔══██╗██║   ██║██║ ██╔╝    ██╔══██╗██║  ██║██╔═══██╗████╗  ██║██╔════╝
  ██████╔╝██║   ██║█████╔╝     ██████╔╝███████║██║   ██║██╔██╗ ██║█████╗
  ██╔══██╗██║   ██║██╔═██╗     ██╔═══╝ ██╔══██║██║   ██║██║╚██╗██║██╔══╝
  ██║  ██║╚██████╔╝██║  ██╗    ██║     ██║  ██║╚██████╔╝██║ ╚████║███████╗
  ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝    ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝
BANNER
printf '%b\n' "${c_reset}"
printf '%b\n' "${c_grey}  Phone Number OSINT Toolkit  |  v${VERSION}  |  installer${c_reset}"
printf '%b\n' "${c_yellow}  Offline public-data analysis only - no live location tracking${c_reset}"
echo

# ---------------------------------------------------------------------------
# 1. Python
# ---------------------------------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
  if [ "${INSTALL_DEPS}" -eq 1 ] && command -v pkg >/dev/null 2>&1; then
    say "python3 not found - installing via pkg..."
    pkg install -y python || fail "Could not install python. Run: pkg install python"
  else
    fail "python3 is required. Install it with: pkg install python"
  fi
fi
PY_VER="$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
ok "Python ${PY_VER} found"

python3 - <<'PYCHECK' || fail "Python 3.8 or newer is required."
import sys
sys.exit(0 if sys.version_info >= (3, 8) else 1)
PYCHECK

# ---------------------------------------------------------------------------
# 2. Optional tools
# ---------------------------------------------------------------------------
if [ "${INSTALL_DEPS}" -eq 1 ] && command -v pkg >/dev/null 2>&1; then
  echo
  warn "Optional: 'termux-api' adds clipboard and notification helpers."
  printf '    Install optional packages? [y/N] '
  read -r answer || answer="n"
  case "${answer}" in
    [yY]*)
      pkg install -y termux-api >/dev/null 2>&1 && ok "termux-api installed" \
        || warn "termux-api install skipped"
      ;;
    *) say "Skipping optional packages." ;;
  esac
fi

# ---------------------------------------------------------------------------
# 3. Copy files
# ---------------------------------------------------------------------------
say "Installing to ${LIB_DIR}"
mkdir -p "${LIB_DIR}" "${BIN_DIR}"

for item in app.py ruk_phoneinfo README.md LICENSE CHANGELOG.md; do
  if [ -e "${SRC_DIR}/${item}" ]; then
    rm -rf "${LIB_DIR:?}/${item}"
    cp -R "${SRC_DIR}/${item}" "${LIB_DIR}/"
  fi
done
ok "Application files copied"

# ---------------------------------------------------------------------------
# 4. Launcher
# ---------------------------------------------------------------------------
cat > "${BIN_DIR}/${APP_SLUG}" <<LAUNCHER
#!/usr/bin/env sh
exec python3 "${LIB_DIR}/app.py" "\$@"
LAUNCHER
chmod 755 "${BIN_DIR}/${APP_SLUG}"

cat > "${BIN_DIR}/ruk" <<LAUNCHER
#!/usr/bin/env sh
exec python3 "${LIB_DIR}/app.py" "\$@"
LAUNCHER
chmod 755 "${BIN_DIR}/ruk"
ok "Commands installed: ${APP_SLUG}, ruk"

# ---------------------------------------------------------------------------
# 5. PATH hint
# ---------------------------------------------------------------------------
case ":${PATH}:" in
  *":${BIN_DIR}:"*) ok "${BIN_DIR} is already on PATH" ;;
  *)
    warn "${BIN_DIR} is not on PATH. Add it with:"
    printf '    %b\n' "${c_grey}echo 'export PATH=\"${BIN_DIR}:\$PATH\"' >> ~/.bashrc && source ~/.bashrc${c_reset}"
    ;;
esac

# ---------------------------------------------------------------------------
# 6. Self test
# ---------------------------------------------------------------------------
if [ "${INSTALL_DEPS}" -eq 1 ]; then
  echo
  say "Running the test suite..."
  if ( cd "${LIB_DIR}" && RUK_ACCEPT_TERMS=1 NO_COLOR=1 \
       python3 -m unittest discover -s tests -p 'test_*.py' >/dev/null 2>&1 ); then
    ok "All tests passed"
  else
    warn "Some tests did not pass - run them manually to see why:"
    printf '    %b\n' "${c_grey}cd ${LIB_DIR} && python3 -m unittest discover -s tests${c_reset}"
  fi
fi

echo
ok "${APP_NAME} v${VERSION} installed."
echo
printf '%b\n' "  ${c_grey}Run the interactive menu:${c_reset}  ${APP_SLUG}"
printf '%b\n' "  ${c_grey}Analyse a number:${c_reset}         ${APP_SLUG} info +923001234567"
printf '%b\n' "  ${c_grey}Show help:${c_reset}                ${APP_SLUG} --help"
echo
printf '%b\n' "  ${c_yellow}Use only on your own numbers, or numbers you are authorised to analyse.${c_reset}"
echo
