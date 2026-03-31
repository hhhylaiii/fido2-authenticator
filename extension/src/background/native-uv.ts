const UV_NATIVE_HOST = "com.scalebear.pqwebauthn_uv";
const DEFAULT_TIMEOUT_MS = 15_000;

interface TouchIdUvRequest {
  type: "uv-request";
  requestId: string;
  operation: "create" | "get";
  rpId: string;
  origin: string;
  reason: string;
  timeoutMs: number;
}

interface TouchIdUvResponse {
  type: "uv-result";
  requestId: string;
  ok: boolean;
  message?: string;
}

interface TouchIdUvStatusRequest {
  type: "uv-status";
  requestId: string;
}

interface TouchIdUvStatusResponse {
  type: "uv-status-result";
  requestId: string;
  ok: boolean;
  version?: string;
  platform?: string;
  message?: string;
}

export interface NativeUvHostStatus {
  ready: boolean;
  host: string;
  version?: string;
  platform?: string;
  detail: string;
}

function toError(message: string): Error & { name: string } {
  const error = new Error(message) as Error & { name: string };
  error.name = "NotAllowedError";
  return error;
}

function assertNativeMessagingAvailable(): void {
  if (!globalThis.chrome?.runtime?.connectNative) {
    throw toError("Native Messaging API is unavailable");
  }
}

function mapNativeHostError(message: string): string {
  const lower = message.toLowerCase();
  if (lower.includes("specified native messaging host not found")) {
    return "Touch ID native host 尚未安裝。請執行：bun run setup:touch-id:macos -- <CHROME_EXTENSION_ID>";
  }
  if (lower.includes("forbidden")) {
    return "Native host 拒絕存取（extension id 不在 allowlist）。請重新安裝 native host manifest。";
  }
  if (lower.includes("has exited")) {
    return "Native host 已提前結束。請先重新編譯並安裝 native host。";
  }
  return message;
}

export async function verifyTouchIdWithNativeHost(input: {
  operation: "create" | "get";
  rpId: string;
  origin: string;
  timeoutMs?: number;
}): Promise<void> {
  assertNativeMessagingAvailable();

  const requestId = crypto.randomUUID();
  const timeoutMs = input.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const request: TouchIdUvRequest = {
    type: "uv-request",
    requestId,
    operation: input.operation,
    rpId: input.rpId,
    origin: input.origin,
    reason:
      input.operation === "create"
        ? "Verify with Touch ID to register this passkey"
        : "Verify with Touch ID to sign in",
    timeoutMs
  };

  return await new Promise<void>((resolve, reject) => {
    const port = chrome.runtime.connectNative(UV_NATIVE_HOST);
    let settled = false;

    const finish = (error?: Error): void => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timer);
      port.onMessage.removeListener(onMessage);
      port.onDisconnect.removeListener(onDisconnect);
      try {
        port.disconnect();
      } catch {
        // ignore disconnect failures during cleanup
      }
      if (error) {
        reject(error);
      } else {
        resolve();
      }
    };

    const onMessage = (message: TouchIdUvResponse): void => {
      if (!message || message.type !== "uv-result" || message.requestId !== requestId) {
        return;
      }
      if (message.ok) {
        finish();
        return;
      }
      finish(toError(message.message ?? "Touch ID verification failed"));
    };

    const onDisconnect = (): void => {
      if (settled) {
        return;
      }
      const runtimeMessage = chrome.runtime.lastError?.message;
      finish(
        toError(
          mapNativeHostError(runtimeMessage ?? "Native host disconnected before UV completed")
        )
      );
    };

    const timer = setTimeout(() => {
      finish(toError("Touch ID verification timed out"));
    }, timeoutMs + 2_000);

    port.onMessage.addListener(onMessage);
    port.onDisconnect.addListener(onDisconnect);
    port.postMessage(request);
  });
}

export async function checkNativeUvHostStatus(): Promise<NativeUvHostStatus> {
  if (!globalThis.chrome?.runtime?.connectNative) {
    return {
      ready: false,
      host: UV_NATIVE_HOST,
      detail: "Native Messaging API is unavailable"
    };
  }

  const requestId = crypto.randomUUID();
  const request: TouchIdUvStatusRequest = {
    type: "uv-status",
    requestId
  };

  return await new Promise<NativeUvHostStatus>((resolve) => {
    const port = chrome.runtime.connectNative(UV_NATIVE_HOST);
    let settled = false;

    const finish = (status: NativeUvHostStatus): void => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timer);
      port.onMessage.removeListener(onMessage);
      port.onDisconnect.removeListener(onDisconnect);
      try {
        port.disconnect();
      } catch {
        // ignore cleanup failure
      }
      resolve(status);
    };

    const onMessage = (message: TouchIdUvStatusResponse): void => {
      if (!message || message.type !== "uv-status-result" || message.requestId !== requestId) {
        return;
      }
      if (message.ok) {
        finish({
          ready: true,
          host: UV_NATIVE_HOST,
          version: message.version,
          platform: message.platform,
          detail: message.message ?? "ready"
        });
        return;
      }
      finish({
        ready: false,
        host: UV_NATIVE_HOST,
        detail: mapNativeHostError(message.message ?? "Native host reported unavailable")
      });
    };

    const onDisconnect = (): void => {
      if (settled) {
        return;
      }
      const runtimeMessage = chrome.runtime.lastError?.message;
      finish({
        ready: false,
        host: UV_NATIVE_HOST,
        detail: mapNativeHostError(runtimeMessage ?? "Native host disconnected")
      });
    };

    const timer = setTimeout(() => {
      finish({
        ready: false,
        host: UV_NATIVE_HOST,
        detail: "Native host status check timeout"
      });
    }, 4_000);

    port.onMessage.addListener(onMessage);
    port.onDisconnect.addListener(onDisconnect);
    port.postMessage(request);
  });
}
