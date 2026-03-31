#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEPS_DIR="$ROOT_DIR/.deps"
EM_CACHE_DIR="${EM_CACHE:-$DEPS_DIR/emscripten-cache}"
LIBOQS_SRC_DIR="${LIBOQS_SRC_DIR:-$DEPS_DIR/liboqs-emscripten-src}"
LIBOQS_BUILD_DIR="${LIBOQS_BUILD_DIR:-$DEPS_DIR/liboqs-emscripten-build}"
LIBOQS_REPO="${LIBOQS_REPO:-https://github.com/open-quantum-safe/liboqs.git}"
LIBOQS_REF="${LIBOQS_REF:-main}"
LIBOQS_MINIMAL_BUILD="${LIBOQS_MINIMAL_BUILD:-SIG_ml_dsa_44;SIG_ml_dsa_65;SIG_ml_dsa_87}"

if ! command -v git >/dev/null 2>&1; then
  echo "[setup:liboqs] git not found" >&2
  exit 1
fi

if ! command -v emcmake >/dev/null 2>&1; then
  echo "[setup:liboqs] emcmake not found. Activate Emscripten SDK first." >&2
  exit 1
fi

if ! command -v cmake >/dev/null 2>&1; then
  echo "[setup:liboqs] cmake not found" >&2
  exit 1
fi

GENERATOR="${CMAKE_GENERATOR:-}"
if [[ -z "$GENERATOR" ]]; then
  if command -v ninja >/dev/null 2>&1; then
    GENERATOR="Ninja"
  else
    GENERATOR="Unix Makefiles"
  fi
fi

mkdir -p "$DEPS_DIR"
mkdir -p "$EM_CACHE_DIR"
export EM_CACHE="$EM_CACHE_DIR"

if [[ ! -d "$LIBOQS_SRC_DIR/.git" ]]; then
  echo "[setup:liboqs] cloning $LIBOQS_REPO -> $LIBOQS_SRC_DIR"
  git clone "$LIBOQS_REPO" "$LIBOQS_SRC_DIR"
fi

echo "[setup:liboqs] preparing source ref: $LIBOQS_REF"
cd "$LIBOQS_SRC_DIR"
git fetch --all --tags --quiet || true
git checkout "$LIBOQS_REF"

if [[ -d "$LIBOQS_BUILD_DIR" ]]; then
  echo "[setup:liboqs] resetting build dir: $LIBOQS_BUILD_DIR"
  rm -rf "$LIBOQS_BUILD_DIR"
fi
mkdir -p "$LIBOQS_BUILD_DIR"

echo "[setup:liboqs] configuring emscripten build"
emcmake cmake -S "$LIBOQS_SRC_DIR" -B "$LIBOQS_BUILD_DIR" \
  -G "$GENERATOR" \
  -DBUILD_SHARED_LIBS=OFF \
  -DOQS_BUILD_ONLY_LIB=ON \
  -DOQS_USE_OPENSSL=OFF \
  -DOQS_DIST_BUILD=OFF \
  -DOQS_MINIMAL_BUILD="$LIBOQS_MINIMAL_BUILD" \
  -DCMAKE_BUILD_TYPE=Release

echo "[setup:liboqs] building liboqs.a"
cmake --build "$LIBOQS_BUILD_DIR" -j

echo "[setup:liboqs] done"
echo "[setup:liboqs] minimal build: $LIBOQS_MINIMAL_BUILD"
echo "[setup:liboqs] include: $LIBOQS_BUILD_DIR/include"
echo "[setup:liboqs] static lib: $LIBOQS_BUILD_DIR/lib/liboqs.a"
