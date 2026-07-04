from __future__ import annotations

import os
from dataclasses import dataclass
from fnmatch import fnmatch


LEGACY_PROTOCOL_VERSION = "2025-03-26"


@dataclass(frozen=True)
class RuntimeConfig:
    auth_mode: str
    bearer_token: str | None
    allowed_origins: tuple[str, ...]
    request_timeout_seconds: int
    max_body_bytes: int

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        auth_mode = os.environ.get("CHECKTIME_AUTH_MODE", "off").strip().lower() or "off"
        bearer_token = os.environ.get("CHECKTIME_BEARER_TOKEN") or None
        allowed_origins = tuple(
            origin.strip()
            for origin in os.environ.get("CHECKTIME_ALLOWED_ORIGINS", "").split(",")
            if origin.strip()
        )
        request_timeout_seconds = parse_positive_int(
            os.environ.get("CHECKTIME_REQUEST_TIMEOUT_SECONDS"),
            default=10,
        )
        max_body_bytes = parse_positive_int(
            os.environ.get("CHECKTIME_MAX_BODY_BYTES"),
            default=1048576,
        )
        return cls(
            auth_mode=auth_mode,
            bearer_token=bearer_token,
            allowed_origins=allowed_origins,
            request_timeout_seconds=request_timeout_seconds,
            max_body_bytes=max_body_bytes,
        )

    @property
    def auth_ready(self) -> bool:
        if self.auth_mode == "off":
            return True
        if self.auth_mode == "bearer":
            return bool(self.bearer_token)
        return False

    @property
    def origin_policy(self) -> str:
        return "allowlist" if self.allowed_origins else "local_relaxed"


def parse_positive_int(raw_value: str | None, default: int) -> int:
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


def is_origin_allowed(origin: str, allowed_origins: tuple[str, ...]) -> bool:
    if not allowed_origins:
        return True
    return any(fnmatch(origin, pattern) for pattern in allowed_origins)
