"""
Phoenix Tracer for P&ID Assistant

Provides OpenTelemetry tracing integration with Arize Phoenix
for LLM observability and monitoring.

Usage:
    from app.phoenix_tracer import init_tracing
    init_tracing()  # Call once at startup
"""

import os
from typing import Optional

# Flag to track if tracing is initialized
_tracing_initialized = False


def init_tracing(
    project_name: str = "pid-assistant",
    endpoint: Optional[str] = None,
    enabled: bool = True,
    suppress_errors: bool = True
) -> bool:
    """
    Initialize Phoenix tracing for LLM observability.

    Args:
        project_name: Name of the project in Phoenix UI
        endpoint: Phoenix collector endpoint (default: localhost:4317)
        enabled: Whether to enable tracing (can be disabled for testing)
        suppress_errors: If True, suppress connection errors when Phoenix server isn't running

    Returns:
        True if tracing was initialized successfully, False otherwise
    """
    global _tracing_initialized

    if _tracing_initialized:
        return True

    if not enabled:
        print("Phoenix tracing disabled")
        return False

    # Check environment variable to disable tracing
    if os.getenv("DISABLE_PHOENIX_TRACING", "false").lower() == "true":
        print("Phoenix tracing disabled via environment variable")
        return False

    try:
        # Import Phoenix components
        from phoenix.otel import register
        from openinference.instrumentation.openai import OpenAIInstrumentor

        # Set endpoint if provided
        if endpoint:
            os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = endpoint

        # Suppress gRPC connection errors if server isn't running
        if suppress_errors:
            import logging
            logging.getLogger("opentelemetry.sdk.trace.export").setLevel(logging.CRITICAL)

        # Register tracer provider with Phoenix
        tracer_provider = register(
            project_name=project_name,
            endpoint=endpoint
        )

        # Instrument OpenAI client (used for embeddings)
        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

        _tracing_initialized = True

        print(f"Phoenix tracing initialized")
        print(f"   Project: {project_name}")
        print(f"   Dashboard: http://localhost:6006")
        print(f"   Note: Start Phoenix server with 'phoenix serve' to view traces")
        print()

        return True

    except ImportError as e:
        print(f"Phoenix tracing not available: {e}")
        print("   Install with: pip install arize-phoenix openinference-instrumentation-openai")
        return False

    except Exception as e:
        print(f"Failed to initialize Phoenix tracing: {e}")
        return False


def is_tracing_enabled() -> bool:
    """Check if tracing is currently enabled"""
    return _tracing_initialized


def get_trace_url(trace_id: str) -> str:
    """Get URL to view a specific trace in Phoenix UI"""
    return f"http://localhost:6006/tracing/traces/{trace_id}"


# Auto-initialize if PHOENIX_AUTO_INIT is set
if os.getenv("PHOENIX_AUTO_INIT", "false").lower() == "true":
    init_tracing()
