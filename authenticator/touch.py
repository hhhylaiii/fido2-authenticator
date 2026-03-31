"""Touch ID verification helper using pyobjc when available."""

from __future__ import annotations

import logging
import time
from typing import Protocol

LOGGER = logging.getLogger(__name__)


class UserVerificationError(RuntimeError):
    pass


class UserVerifier(Protocol):
    def verify_user(self, prompt: str | None = None) -> bool:
        ...


class TouchIDVerifier:
    def __init__(self, reason: str = "Authenticate with Touch ID", timeout: int = 30) -> None:
        self.reason = reason
        self.timeout = timeout

    def verify_user(self, prompt: str | None = None) -> bool:
        message = prompt or self.reason
        try:
            from LocalAuthentication import (
                LAPolicyDeviceOwnerAuthenticationWithBiometrics,
                LAContext,
            )
            from Foundation import NSDate, NSRunLoop
        except Exception as exc:  # pragma: no cover - only hit on non-macOS
            raise UserVerificationError(
                "Touch ID is unavailable on this platform."
            ) from exc

        context = LAContext.alloc().init()
        success, error = context.canEvaluatePolicy_error_(
            LAPolicyDeviceOwnerAuthenticationWithBiometrics, None
        )
        if not success:
            raise UserVerificationError(f"Touch ID unavailable: {error}")

        result_holder = {"done": False, "success": False, "error": None}

        def handler(result: bool, err) -> None:
            result_holder["done"] = True
            result_holder["success"] = bool(result)
            result_holder["error"] = err

        context.evaluatePolicy_localizedReason_reply_(
            LAPolicyDeviceOwnerAuthenticationWithBiometrics, message, handler
        )

        run_loop = NSRunLoop.currentRunLoop()
        deadline = time.time() + self.timeout
        while not result_holder["done"] and time.time() < deadline:
            run_loop.runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.1))

        if not result_holder["done"]:
            raise UserVerificationError("Touch ID timed out. Please try again.")
        if not result_holder["success"]:
            raise UserVerificationError("Touch ID verification failed")
        return True


class NoopVerifier:
    """User verifier that unconditionally succeeds (useful on non-macOS)."""

    def verify_user(self, prompt: str | None = None) -> bool:
        LOGGER.info("Skipping user verification: NoopVerifier in use")
        return True


class DummyVerifier:
    """Simple verifier that always prompts via CLI."""

    def verify_user(self, prompt: str | None = None) -> bool:
        msg = prompt or "Confirm authenticator action"
        answer = input(f"{msg} (y/N): ")
        if answer.strip().lower() == "y":
            return True
        raise UserVerificationError("User declined")
