# PQ FIDO2 Authenticator — 專案總覽

> 一份讓你快速掌握整個 repo 全貌的導讀文件。  
> 涵蓋：使用技術、專案架構、目前進度、未完成事項、實際運作方式。

---

## 1. 專案目標（一句話）

打造一個 **支援 Post-Quantum Cryptography（PQC）的 FIDO2 / WebAuthn 認證系統**，  
讓瀏覽器在「不改 W3C WebAuthn API 表面」的前提下，於底層使用 **ML-DSA（CRYSTALS-Dilithium）後量子簽章演算法** 完成註冊與登入流程。

本專案屬於 **Proof-of-Concept (PoC) + 研究性質**，重點在驗證 PQC 整合到 FIDO2 流程的可行性與相容性。

支援演算法（COSE alg id）：

| COSE alg | 對應演算法     | 用途     |
| -------- | -------------- | -------- |
| `-48`    | ML-DSA-44      | 預設     |
| `-49`    | ML-DSA-65      | 中等強度 |
| `-50`    | ML-DSA-87      | 最高強度 |

`credentialPublicKey` 在 COSE_Key 中以 `kty=7 (AKP)` 表示。

---

## 2. 專案發展的兩個階段（Phase）

repo 的目錄結構暗示了兩條主線。對應根目錄的 `phase 1.jpg` 與 `phase 2.jpg` 兩張投影圖（簡報素材）：

### 🟦 Phase 1 — Python Authenticator + 自開發 RP/Frontend（已可運作）

走「**自己當 Authenticator + 自己當 RP**」的整合路線：

- 在 macOS 本機跑一個 **Python authenticator**。
- 用 **Playwright** 開啟 Chromium，**注入 JS** 攔截 `navigator.credentials.create/get`。
- 攔截到的請求送回 Python，呼叫 **Touch ID** 做 User Verification、**liboqs** 產生 ML-DSA keypair、**macOS Keychain (keyring)** 儲存私鑰，最後回傳符合 WebAuthn 形狀的 response。
- 自製 **Flask RP Server** 做 challenge 發放、attestation/assertion 驗證。
- 自製 **Next.js 前端** 做 demo 介面。
- 全部用 `docker compose` 一鍵起 RP + Frontend，authenticator 留在 host 跑（因為要呼叫 Touch ID）。

對應目錄：`authenticator/`、`rp_server/`、`frontend/`、`drizzle/`、`Dockerfile.*`、`docker-compose.yml`、`README.md`。

### 🟧 Phase 2 — Chrome Extension（規格凍結中，PoC trial 已通）

把 Phase 1 的能力搬到「**真實終端使用者可用**」的形態：

- 寫成 **Chrome MV3 Extension**，攔截 WebAuthn 流程。
- PQ 簽章不再依賴本機 `liboqs`，而是把 `liboqs C source` 用 **Emscripten 編成 WASM**，跑在 extension 內。
- v1 鎖定 `https://demo.yubico.com/webauthn-developers` 作為標準 RP 測試對象（不改 RP 端）。
- 強 UV（Touch ID / Windows Hello）走 **Native Messaging Host**（一次性安裝）；預設模式 `soft-auto` 也能用。

對應目錄：`extension/`、`codex/`（規格與安全報告）。

> 兩階段並非互斥，而是同一研究主題的兩種落地方式：Phase 1 驗證完整端到端（含自家 RP），Phase 2 驗證在真實 RP（Yubico demo）上的可行性與分發友善度。

---

## 3. 使用技術全景

### Phase 1（Python Authenticator + Flask RP + Next.js）

| 區塊                | 技術                                                                                        |
| ------------------- | ------------------------------------------------------------------------------------------- |
| 語言 / 套件管理     | Python 3.10+，`uv`                                                                          |
| Authenticator       | `playwright`（Chromium 攔截 + JS 注入）、`pyobjc` + `LocalAuthentication`（Touch ID）       |
| PQC                 | `liboqs-python`（ML-DSA-44/65/87）                                                          |
| 憑證儲存            | `keyring`（macOS Keychain）+ `data/credential_index.json`（純 metadata 索引）              |
| 資料模型 / 驗證     | `pydantic` v2、`pydantic-settings`                                                          |
| RP Server           | `Flask`、`flask-cors`、`SQLAlchemy 2.0`、`cbor2`、`fido2 (cbor)`、SQLite                    |
| 前端                | `Next.js 16`、`React 19`、`TypeScript`、`TailwindCSS 4`、`Shadcn UI`、`react-hook-form`、`zod`、`sonner` |
| 前端套件管理        | `bun`                                                                                       |
| DB 觀測             | `drizzle-kit studio`（讀同一個 SQLite 檔）                                                  |
| 容器化              | `Docker` + `docker compose`（multi-stage build；RP 內預先編 liboqs）                       |
| 測試                | `pytest`（authenticator / rp）、`bun test`（frontend lib）                                  |
| Lint / Typecheck    | `ruff`、`pyright`、`eslint`、`tsc`                                                          |

### Phase 2（Chrome Extension）

| 區塊         | 技術                                                                                |
| ------------ | ----------------------------------------------------------------------------------- |
| Extension    | Chrome MV3（service worker + content script + injected main-world hook）            |
| 構建         | `Vite` + `React` + `TypeScript` + `TailwindCSS`，套件管理用 `bun`                  |
| PQC          | `liboqs` C source（minimal build：只編 `SIG_ml_dsa_44/65/87`）→ Emscripten WASM   |
| 編碼         | Base64URL（無 padding）+ CBOR（手寫 minimal CBOR encoder）+ SHA-256（WebCrypto）   |
| 儲存         | `chrome.storage.local`（schema 化的 `pq_store_v1`，含 legacy migration）           |
| UV（強驗證） | macOS Native Messaging Host（`Swift`，呼叫 `LocalAuthentication` → Touch ID）       |
| 測試         | `bun test`（deterministic seeded fixtures，避免 flaky）                            |
| 平台         | 目前僅 Chrome；macOS UV 已實作，Windows Hello 規劃中                                |

---

## 4. 專案架構

### 4.1 目錄總覽

```text
fido2-authenticator/
├── README.md                # Phase 1 快速啟動（docker compose + uv run）
├── docker-compose.yml       # 啟 rp-server + frontend
├── Dockerfile.rp            # Flask + liboqs 預編譯
├── Dockerfile.frontend      # Next.js bun build
├── pyproject.toml / uv.lock # Phase 1 Python 依賴
│
├── authenticator/           # 【Phase 1】Python 軟體 authenticator
│   ├── __main__.py          #   CLI: `python -m authenticator --url <URL>`
│   ├── bridge.py            #   Playwright Chromium + 攔截 JS 注入
│   ├── service.py           #   Authenticator 核心：make_credential / get_assertion
│   ├── pqcrypto.py          #   liboqs-python wrapper（ML-DSA）
│   ├── webauthn.py          #   COSE_Key / authenticatorData / attestationObject 組裝
│   ├── storage.py           #   Keychain + JSON index
│   ├── touch.py             #   Touch ID via pyobjc / Noop / Dummy verifier
│   ├── models.py            #   Pydantic schemas + CredentialRecord
│   ├── config.py            #   AuthenticatorSettings
│   ├── data/                #   credential index 持久檔
│   └── tests/               #   pytest 單元測試
│
├── rp_server/               # 【Phase 1】Flask RP Server
│   ├── app.py               #   Endpoints: /register/{options,verify}, /authenticate/{options,verify}
│   ├── services.py          #   challenge / origin / rpIdHash / attestation 解析 / 簽章驗證
│   ├── schemas.py           #   Request/Response Pydantic models
│   ├── models.py            #   User / Credential（SQLAlchemy 2.0）
│   ├── challenges.py        #   in-memory ChallengeCache（per-username scope）
│   ├── database.py / config.py
│   └── data/rp.db           #   SQLite（被 docker volume bind 進去）
│
├── frontend/                # 【Phase 1】Next.js demo 前端
│   ├── src/pages/index.tsx  #   Register / Authenticate Tab、信用憑證列表、即時 log
│   ├── src/lib/webauthn.ts  #   buffer ⇄ base64url ⇄ hex 工具與 credential 序列化
│   ├── src/lib/api.ts       #   rpFetch（統一 RP API 呼叫 + 錯誤處理）
│   └── （已安裝完整 Shadcn UI）
│
├── drizzle/                 # 觀測同一個 rp.db 的 Drizzle Studio（`bun run db:studio`）
│
├── extension/               # 【Phase 2】Chrome MV3 PQ WebAuthn Extension
│   ├── public/manifest.json #   MV3 manifest（host_permissions 鎖 demo.yubico.com）
│   ├── src/
│   │   ├── injected/        #   document_start 注入到 main-world，patch navigator.credentials
│   │   ├── content/         #   Isolated world ↔ Page main-world 訊息橋接
│   │   ├── background/      #   Service worker：authenticator、liboqs wasm bridge、native UV
│   │   │   ├── authenticator.ts          # PQAuthenticator（create / get）
│   │   │   ├── liboqs-wasm-signer.ts     # 透過 wasm 呼叫 liboqs
│   │   │   ├── liboqs-wasm-bridge.ts     # WASI imports（random_get 等）
│   │   │   ├── native-uv.ts              # Native Messaging（Touch ID host）
│   │   │   ├── store.ts                  # chrome.storage.local schema
│   │   │   └── pq-signer.ts              # Signer interface
│   │   ├── options/         #   Extension options UI（uvMode 切換、native host 狀態）
│   │   ├── lib/             #   base64url / binary / cbor / sha256 utils
│   │   └── types/messages.ts#   訊息協定型別
│   ├── wasm/pq_bridge.c     #   C bridge for liboqs ML-DSA exports
│   ├── public/wasm/         #   產出的 pq_bridge.wasm
│   ├── scripts/             #   liboqs WASM build / native host build & install
│   ├── native-host/         #   pq_uv_host.swift（macOS Touch ID host）
│   └── package.json         #   bun scripts: setup / build / build:wasm / build:native-host:macos
│
└── codex/                   # 規格、設計與安全報告（給 Agent 用）
    ├── AGENTS.md            #   Abstract: 想做什麼（Phase 2 主軸）
    ├── spec.md              #   完整系統規格（Phase 1 主軸）
    ├── plan.md              #   階段檢查清單（含 [x] / [ ]）
    ├── REPORTS.md           #   v7 評估報告 + Decision Log（最新進度的唯一真相來源）
    ├── specs/PHASE-1-IMPLEMENTATION-SPEC.md   # Extension Phase-1 凍結規格（v0.3-draft）
    ├── docs/                #   API 參考（python-fido2 / liboqs-python / CDP WebAuthn）
    ├── repomix/             #   外部 repo 打包輸出（Yubico python-fido2）
    └── SECURITY_REPORTS/    #   一議題一檔的安全審查 backlog
```

### 4.2 Phase 1 資料流（執行時）

```text
[Browser (Chromium 由 Playwright 開啟)]
    │  navigator.credentials.create({...})
    │  ↓ 被 injected JS 攔截
[Injected JS in page]
    │  序列化 ArrayBuffer → base64url，呼叫 window.__pqMakeCredential
    │  ↓ context binding（Playwright expose_binding）
[Python Authenticator (host process)]
    │  1) Pydantic 驗證 options
    │  2) rpId vs origin host 必須相等
    │  3) Touch ID（TouchIDVerifier via pyobjc）
    │  4) excludeCredentials 檢查
    │  5) liboqs-python 生成 ML-DSA keypair
    │  6) keyring 寫入 Keychain，更新 credential_index.json
    │  7) 組 clientDataJSON / authenticatorData(flags=0x45, signCount=0)
    │  8) 組 attestationObject (fmt="none")
    │  ↓ 回傳 JSON（base64url）
[Injected JS]
    │  把 base64url 還原成 ArrayBuffer，包成 PublicKeyCredential 物件
    │  ↓ 走原生 navigator.credentials.create 的回傳路徑
[Frontend (Next.js)]
    │  serializeAttestation → POST /register/verify
    │  ↓ HTTP JSON
[Flask RP Server]
    │  1) 比對 ChallengeCache pop 出的 challenge
    │  2) 驗證 clientData.type / origin
    │  3) 解 CBOR attestationObject、解 authenticatorData、解 COSE_Key
    │  4) 比對 rpIdHash、檢查 alg ∈ hosted_algorithms
    │  5) 存 Credential 進 SQLite
    │  → success
```

登入流程鏡像：`navigator.credentials.get` → Touch ID → 用儲存的私鑰對 `authData || SHA-256(clientDataJSON)` 簽章 → RP 端用公鑰透過 `oqs.Signature(...).verify(...)` 驗證並遞增 `signCount`。

### 4.3 Phase 2 資料流（Chrome Extension）

```text
[Page main-world JS on demo.yubico.com]
    │  navigator.credentials.create / get
    │  ↓ injected hook patch（document_start）
[Injected JS] ──postMessage──> [Content script (isolated world)]
                                        │
                                        ↓ chrome.runtime.sendMessage
                                [Background service worker]
                                        │ 來源檢查（demo.yubico.com only）
                                        │ PQAuthenticator.makeCredential / getAssertion
                                        │   ├─ performUserVerification
                                        │   │    ├─ soft-auto: no-op
                                        │   │    └─ native-touch-id: 透過 Native Messaging
                                        │   │         呼叫 macOS Swift host → Touch ID
                                        │   ├─ LiboqsWasmSigner（pq_bridge.wasm）
                                        │   │    ML-DSA-44/65/87 keypair / sign
                                        │   └─ chrome.storage.local 寫入 credential
                                        ↓
                                組好 base64url JSON
                                        ↓ 一路回到 page
[Page] 取得 PublicKeyCredential，繼續正常 WebAuthn 流程
```

### 4.4 凍結的編碼／格式契約（兩個 Phase 一致）

- 二進位欄位透過 JSON 傳輸時一律 **base64url（無 padding）**。
- `clientDataJSON` 為 UTF-8 JSON bytes；包含 `crossOrigin: false`。
- `rpIdHash = SHA-256(rpId)`（IDNA 正規化）。
- Assertion 簽章輸入：`authenticatorData || SHA-256(clientDataJSON)`。
- `authenticatorData` flags：
  - 註冊：`UP+UV+AT = 0x45`、`signCount = 0`
  - 登入：`UP+UV = 0x05`、`signCount += 1`
- `attestationObject` 一律 `fmt: "none"`（即使 RP 要求 `direct` 也照樣回 none — v0.1 trial baseline）。
- `credentialPublicKey`（COSE_Key）：`1=7 (AKP)`、`3=alg`、`-1=public key bytes`，沒有舊版 `-70001` marker。
- AAGUID 全零（16 bytes）。

---

## 5. 目前進度

### 5.1 Phase 1 — Python Authenticator + Flask RP + Next.js

`codex/plan.md` 顯示幾乎全部完成：

| 階段                                  | 狀態 |
| ------------------------------------- | ---- |
| 開發環境與框架建立                    | ✅   |
| Authenticator 實作（make/get + PQC + Touch ID + Keychain） | ✅   |
| RP Server 實作（4 個 endpoints + 簽章驗證） | ✅   |
| Frontend 註冊／登入頁、credential 面板  | ✅   |
| Pytest / bun test / Playwright E2E    | ✅   |
| Docker 化（multi-stage + liboqs 預編譯） | ✅   |
| **與 Yubico Demo 兼容性驗證**         | ❌   |

實際可運作證據：

- `docker compose up -d` 起 RP（:5005）+ Frontend（:3000）。
- `uv run python -m authenticator --url http://localhost:3000` 起 Chromium 並注入攔截。
- `authenticator/data/credential_index.json` 有歷史憑證紀錄（`4f0507d` commit 中有更新）。
- 前端會即時呼叫 `window.__pqListCredentials()` 顯示目前 Keychain 內憑證。

### 5.2 Phase 2 — Chrome Extension

`codex/REPORTS.md` Decision Log 已記錄到 #39（2026-02-08）：

已完成：

- ✅ MV3 骨架（background / content / injected / options）
- ✅ M1 註冊流程凍結（PHASE-1-IMPLEMENTATION-SPEC v0.3-draft）
- ✅ M2 登入流程凍結（含 signCount 持久化）
- ✅ liboqs C → Emscripten WASM 整合（minimal build 三個 ML-DSA）
- ✅ CSP `'wasm-unsafe-eval'`、WASI imports 補齊
- ✅ COSE key 改為 `kty=7 (AKP)`，移除自訂 marker
- ✅ `chrome.storage.local` schema 化（含 legacy migration）
- ✅ macOS Native Messaging Host（Swift）+ Touch ID UV（一鍵安裝腳本）
- ✅ Options UI：`uvMode` 切換、native host ready/version 狀態檢查
- ✅ `bun run typecheck` / `bun run test` / `bun run build` 全部通過
- ✅ **Yubico demo 上 PQ 註冊 + PQ 認證已可走通**（trial baseline）

### 5.3 安全議題追蹤（`codex/SECURITY_REPORTS/`）

| #   | 議題                                          | 狀態         |
| --- | --------------------------------------------- | ------------ |
| 001 | 明文私鑰儲存                                  | 📋 待修補    |
| 002 | 未受信任的網頁可觸發 UV（缺 user gesture）    | 📋 待修補    |
| 003 | Runtime schema 驗證缺漏                       | 📋 待修補    |
| 004 | signCount 競態條件                            | 📋 待修補    |
| 005 | liboqs 未鎖版本（supply chain）              | 📋 待修補    |
| 006 | Production sourcemap 暴露                     | 📋 待修補    |
| 007 | CSP / resource surface 收斂                   | 📋 待修補    |
| UV  | 強 UV 安全議題                                | ⏸ Deferred（最後階段處理） |

最新 git history 的 4 個 commits（`9a5cc4d`, `4f0507d`, `ca4db14`, `854ca31`）顯示近期重點放在 **Docker 化 Phase 1**，extension 改動暫時停留在規格凍結 + trial 通過的狀態。

---

## 6. 還未完成的進度（重點 backlog）

### 🟦 Phase 1 剩餘

1. **與 Yubico Demo 的兼容性驗證**（`plan.md` 中唯一未勾選項）  
   即把 Phase 1 的 Python authenticator 接到 `https://demo.yubico.com/webauthn-developers`，  
   驗證自家 authenticator 能否在標準 RP 上完成註冊與登入。  
   實作上 Phase 2 已用 extension 走通類似流程，可作為對照。

### 🟧 Phase 2 剩餘

1. **規格從 v0.3-draft 邁向穩定版**（PHASE-1-IMPLEMENTATION-SPEC）。
2. **強 UV 的正式整合決策**：
   - 純 extension 軟體 UV vs Native Messaging Host 路線取捨。
   - Windows Hello host 擴充（沿用同一 `uv-request / uv-result / uv-status` 協定）。
3. **安全 backlog（001–007）逐項修補**，特別是：
   - 私鑰加密包裝（不要直接 base64url 存到 `chrome.storage.local`）。
   - User gesture gate（避免被惡意網頁靜默觸發 UV）。
   - 嚴格的 runtime schema 驗證（boundary 層 schema）。
   - signCount 競態保護（write-after-sign 的原子性）。
   - liboqs source pinning。
   - Production sourcemap 不可暴露。
4. **發佈通路**：目前只有 unpacked `dist/` 載入，沒有打包成 Chrome Web Store 上架版本。
5. **跨瀏覽器支援**：目前只跑 Chrome（MV3），其他瀏覽器在 Out-of-scope。
6. **Fallback 策略**：目前是 PQ-only，不會 fallback 到傳統演算法（這是設計決策，不是 bug）。

### 🟫 通用 backlog

- 與標準 `python-fido2` / WebAuthn server library 的 CBOR/COSE 完整相容（目前用自製 CBOR 為主）。
- 完整 E2E 測試（Phase 2 在 demo.yubico.com 的自動化 trial run）。
- `phase 1.jpg` / `phase 2.jpg`（剛新增到 `git status`）兩張投影圖尚未進 commit。

---

## 7. 專案運作方式（怎麼跑起來）

### 7.1 Phase 1 — 在 macOS 跑完整端到端

```bash
# 1) 起 RP Server + Frontend
docker compose up -d
#    → Frontend: http://localhost:3000
#    → RP:       http://localhost:5005

# 2) 起 Python authenticator（macOS host，因為要 Touch ID）
uv run python -m authenticator --url http://localhost:3000
#    → 會開一個 Chromium 視窗，自動載入前端
```

接著：

1. 在 Chromium 視窗的 Register tab 填 username/displayName、選 ML-DSA 演算法，點 **Create credential**。
2. macOS 跳 Touch ID 提示 → 通過後在 Keychain 寫入私鑰、RP DB 寫入公鑰。
3. 切到 Authenticate tab，點 **Request assertion** → 再次 Touch ID → 驗證成功。

選用：

```bash
# 觀察 RP / Frontend log
docker compose logs -f

# 觀察 SQLite（drizzle studio，讀同一個 rp.db）
cd drizzle && bun install && bun run db:studio
#    → https://local.drizzle.studio

# 停止
docker compose down
```

注意：authenticator 因為要呼叫 macOS Touch ID + Keychain + 開啟真實 GUI Chromium，**無法 dockerize**，必須在 macOS host 跑。

### 7.2 Phase 2 — Chrome Extension（PoC trial）

```bash
cd extension

# 1) 安裝 + 編 liboqs WASM（要有 emcc / cmake）
bun install
bun run setup          # = setup:liboqs:wasm + build:wasm

# 2) 編 extension bundle
bun run build          # 或 `bun run build:all` 連 wasm 一起重編
```

載入 extension：

1. Chrome 開 `chrome://extensions`，啟用 Developer mode。
2. **Load unpacked** → 選 `extension/dist`。
3. 取得 Extension ID。
4. 開啟 `https://demo.yubico.com/webauthn-developers`，extension 會自動攔截。

選用：開啟 Touch ID 強 UV（macOS）：

```bash
bun run setup:touch-id:macos -- <CHROME_EXTENSION_ID>
#    = build native host (Swift) + 安裝 NativeMessagingHosts manifest
# 然後到 extension options 把 uvMode 切到 native-touch-id
```

測試：

```bash
bun run typecheck
bun run test
```

---

## 8. 關鍵設計決策（速查表）

> 來自 `codex/REPORTS.md` Decision Log，按時間倒序挑重點。

| 決策                                          | 註                                                      |
| --------------------------------------------- | ------------------------------------------------------- |
| **PQ-only**，不做 fallback                    | Phase 2 v1                                              |
| 支援 `-48/-49/-50`，預設 `-48`               | Phase 2；Phase 1 預設 `-49`（見 `rp_server/config.py`） |
| `attestation` 一律回 `fmt=none`              | 即使 RP 要 `direct`                                     |
| `kty=7 (AKP)` for COSE_Key                    | 移除舊版自訂 `-70001`                                   |
| `flags`：create=`0x45`、get=`0x05`            | `signCount` 註冊為 0、登入每次 +1                       |
| Phase 2 鎖定 `demo.yubico.com`                | 未來再開放任意網域                                      |
| Extension 用 WASM，避免要求終端裝本機 liboqs  | 強 UV 才需要 Native Host                                |
| 強 UV = macOS Native Messaging Host           | Windows Hello 規劃中                                    |
| 安全 backlog 一議題一檔（`SECURITY_REPORTS/`）| 方便逐項 PR + 教學                                      |
| UV 安全議題明確列為 **deferred**              | 排在最後階段做                                          |

---

## 9. 想接手或繼續做？建議閱讀順序

1. `codex/AGENTS.md`（5 分鐘了解 Phase 2 想做什麼）
2. `codex/spec.md`（10 分鐘了解 Phase 1 完整規格）
3. `codex/plan.md`（看每階段 checkbox）
4. `codex/REPORTS.md`（**最重要**，所有最新決策都在這裡）
5. `codex/specs/PHASE-1-IMPLEMENTATION-SPEC.md`（Phase 2 凍結規格）
6. `codex/SECURITY_REPORTS/*.md`（接手安全議題前必讀）
7. 程式碼入口：
   - Phase 1：`authenticator/service.py` → `authenticator/bridge.py` → `rp_server/app.py`
   - Phase 2：`extension/src/background/authenticator.ts` → `extension/src/injected/index.ts`
