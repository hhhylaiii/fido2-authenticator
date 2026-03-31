# PQ FIDO2 Authenticator

## 快速開始

### 前置需求

- [Docker](https://www.docker.com/) (RP Server + Frontend)
- [uv](https://docs.astral.sh/uv/) (Python Authenticator)

### 步驟 1 — 啟動 RP Server 與前端

```bash
docker compose up -d
```

第一次執行會 build image，之後重啟很快。

- 前端：http://localhost:3000
- RP Server：http://localhost:5005

### 步驟 2 — 啟動 Authenticator

```bash
uv run python -m authenticator --url http://localhost:3000
```

Authenticator 會開啟一個 Chromium 視窗，並攔截 WebAuthn API。

---

## 選用功能

### 停止服務

```bash
docker compose down
```

### 查看 RP Server 與前端 logs

```bash
docker compose logs -f
```

### Database Studio（觀察 DB 資料）

```bash
cd drizzle
bun install
bun run db:studio
```

開啟瀏覽器到 https://local.drizzle.studio

---

## 注意事項

Authenticator 需在 macOS 本機執行，無法 Dockerize，原因如下：

- 使用 macOS Touch ID 進行使用者驗證
- 使用 macOS Keychain 儲存憑證
- Playwright 需要開啟真實 GUI 視窗
