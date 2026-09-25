#!/usr/bin/env bash
# install.sh <provider> <bin-dir> - make the provider's MCP server runnable, for CI.
#
# github: downloads the pinned github-mcp-server release named in
#         providers/github.json into <bin-dir> and checks its sha256. Put
#         <bin-dir> on PATH afterwards.
# gitlab: the server runs through `npx` at the version pinned in
#         providers/gitlab.json; this only checks npx is there.
#
# Already on PATH (a runner image that ships it) -> nothing to do.
set -euo pipefail

provider="${1:?usage: install.sh <provider> <bin-dir>}"
bindir="${2:?usage: install.sh <provider> <bin-dir>}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
profile="$here/providers/$provider.json"
[ -f "$profile" ] || { echo "install.sh: no profile for provider '$provider'" >&2; exit 2; }

# field <key>... - one value from the profile, by key path.
field() { python3 -c 'import json,sys; d=json.load(open(sys.argv[1]))
for k in sys.argv[2:]: d=d[k]
print(d)' "$profile" "$@"; }

case "$provider" in
  github)
    binary="$(field install binary)"
    if command -v "$binary" >/dev/null 2>&1; then exit 0; fi
    case "$(uname -m)" in
      x86_64|amd64) arch=x86_64 ;;
      aarch64|arm64) arch=arm64 ;;
      *) echo "install.sh: no pinned $binary build for $(uname -m)" >&2; exit 2 ;;
    esac
    url="$(field install url)"; url="${url//\{arch\}/$arch}"
    sum="$(field install sha256 "$arch")"
    tmp="$(mktemp -d)"
    curl -fsSL --retry 3 -o "$tmp/server.tgz" "$url"
    echo "$sum  $tmp/server.tgz" | sha256sum -c --quiet - \
      || { echo "install.sh: checksum mismatch for $url" >&2; exit 1; }
    mkdir -p "$bindir"
    tar -xzf "$tmp/server.tgz" -C "$tmp" "$binary"
    install -m 0755 "$tmp/$binary" "$bindir/$binary"
    rm -rf "$tmp"
    ;;
  gitlab)
    command -v npx >/dev/null 2>&1 || { echo "install.sh: the GitLab MCP server runs through npx; use an image with Node.js 20+" >&2; exit 2; }
    ;;
  *)
    echo "install.sh: nothing to install for '$provider'" >&2
    ;;
esac
