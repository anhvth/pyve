#!/bin/sh

is_uv_installed() {
  command -v uv >/dev/null 2>&1
}
is_curl_installed() {
  command -v curl >/dev/null 2>&1
}
if ! is_curl_installed; then
  apt-get update && apt-get install -y curl
fi


if ! is_uv_installed; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

export PATH="$HOME/.local/bin:$PATH"

echo "uv is installed"

/root/.local/bin/uv python install 3.9 3.10 3.11
