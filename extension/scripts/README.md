# `scripts/`

Automation scripts used by `package.json` commands.

## `setup-liboqs-emscripten.sh`

Purpose:

1. prepare local `liboqs` source in `.deps/liboqs-emscripten-src`
2. configure an Emscripten build directory
3. build static library `.deps/liboqs-emscripten-build/lib/liboqs.a`

Important behavior:

1. auto-detects CMake generator (`Ninja` if available, otherwise `Unix Makefiles`)
2. resets build dir on each run to avoid stale toolchain cache issues
3. sets local `EM_CACHE` under `.deps/emscripten-cache`
4. compiles minimal algorithms only:
   1. `SIG_ml_dsa_44`
   2. `SIG_ml_dsa_65`
   3. `SIG_ml_dsa_87`

Main env vars:

1. `LIBOQS_REPO`
2. `LIBOQS_REF`
3. `LIBOQS_SRC_DIR`
4. `LIBOQS_BUILD_DIR`
5. `LIBOQS_MINIMAL_BUILD`
6. `EM_CACHE`

## `build-liboqs-wasm.sh`

Purpose:

1. compile/link `wasm/pq_bridge.c` + `liboqs.a`
2. output `public/wasm/pq_bridge.wasm`

Input resolution order:

1. explicit env (`LIBOQS_INCLUDE_DIR`, `LIBOQS_STATIC_LIB`)
2. `LIBOQS_DIR` (include/lib or build/include/build/lib)
3. project-local `.deps/liboqs-emscripten-build`

Main env vars:

1. `LIBOQS_DIR`
2. `LIBOQS_INCLUDE_DIR`
3. `LIBOQS_STATIC_LIB`
4. `EM_CACHE`

## Common Failures

1. `Could not resolve host: github.com`
   1. Network/DNS issue when fetching liboqs.
2. `Missing LIBOQS include path`
   1. Run `bun run setup:liboqs:wasm` first.
3. `CMAKE generator mismatch`
   1. Script auto-resets build dir; rerun setup.
4. wasm CSP/runtime errors in extension
   1. Ensure extension reloaded from latest `dist/`.

## `build-native-host-macos.sh`

Purpose:

1. compile `native-host/pq_uv_host.swift`
2. output native host binary at `.native-host/bin/pq_uv_host`

Requirements:

1. macOS
2. Xcode Command Line Tools (`xcrun`, `swiftc`)

## `install-native-host-macos.sh`

Purpose:

1. install Chrome Native Messaging host manifest for Touch ID UV
2. register host name `com.scalebear.pqwebauthn_uv`

Usage:

1. `bash scripts/install-native-host-macos.sh <CHROME_EXTENSION_ID>`
2. optional second arg: host binary absolute path

Behavior:

1. writes manifest to:
   1. `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.scalebear.pqwebauthn_uv.json`
2. allowlist origin:
   1. `chrome-extension://<CHROME_EXTENSION_ID>/`

## `setup-touch-id-uv-macos.sh`

Purpose:

1. one-shot setup for Touch ID UV
2. run build + install in sequence

Usage:

1. `bash scripts/setup-touch-id-uv-macos.sh <CHROME_EXTENSION_ID>`
2. or set env:
   1. `CHROME_EXTENSION_ID=<id> bash scripts/setup-touch-id-uv-macos.sh`

Note:

1. this script cannot auto-reload extension or auto-change options page settings
