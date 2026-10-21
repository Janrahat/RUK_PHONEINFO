#!/data/data/com.termux/files/usr/bin/bash
#
# RUK_PHONEINFO uninstaller.
#
#   bash uninstall.sh --dry-run   # show what would be removed
#   bash uninstall.sh             # remove the installed files
#   bash uninstall.sh --purge     # also remove ~/.ruk_phoneinfo (config)
#
set -euo pipefail

APP_SLUG="ruk_phoneinfo"
PREFIX="${HOME}/.local"
DRY_RUN=0
PURGE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --purge) PURGE=1 ;;
    --prefix) shift; PREFIX="${1:-$PREFIX}" ;;
    -h|--help)
      sed -n '2,9p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

BIN_DIR="${PREFIX}/bin"
LIB_DIR="${PREFIX}/lib/${APP_SLUG}"
CONFIG_DIR="${HOME}/.${APP_SLUG}"

c_reset='\033[0m'; c_cyan='\033[38;5;80m'; c_green='\033[38;5;114m'
c_yellow='\033[38;5;221m'; c_grey='\033[38;5;245m'

say()  { printf '%b\n' "${c_cyan}[*]${c_reset} $*"; }
ok()   { printf '%b\n' "${c_green}[+]${c_reset} $*"; }
warn() { printf '%b\n' "${c_yellow}[!]${c_reset} $*"; }

TARGETS="${BIN_DIR}/${APP_SLUG} ${BIN_DIR}/ruk ${LIB_DIR}"
if [ "${PURGE}" -eq 1 ]; then
  TARGETS="${TARGETS} ${CONFIG_DIR}"
fi

if [ "${DRY_RUN}" -eq 1 ]; then
  say "Dry run - nothing will be removed."
  for target in ${TARGETS}; do
    if [ -e "${target}" ]; then
      printf '    %b\n' "${c_grey}would remove:${c_reset} ${target}"
    else
      printf '    %b\n' "${c_grey}not present:${c_reset}  ${target}"
    fi
  done
  echo
  warn "Re-run without --dry-run to actually remove these paths."
  exit 0
fi

say "Removing ${APP_SLUG}..."
for target in ${TARGETS}; do
  if [ -e "${target}" ]; then
    rm -rf "${target}"
    ok "Removed ${target}"
  else
    printf '    %b\n' "${c_grey}not present:${c_reset} ${target}"
  fi
done

echo
ok "Uninstall complete."
if [ "${PURGE}" -eq 0 ] && [ -d "${CONFIG_DIR}" ]; then
  warn "Your config was kept at ${CONFIG_DIR} (use --purge to remove it)."
fi
echo
