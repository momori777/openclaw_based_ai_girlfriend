"""Minimal telemetry stub — avoids missing mem0.memory subpackage."""

def capture_client_event(*args, **kwargs):
    """No-op telemetry for local-only use."""
    pass

def capture_event(*args, **kwargs):
    """No-op telemetry for local-only use."""
    pass
