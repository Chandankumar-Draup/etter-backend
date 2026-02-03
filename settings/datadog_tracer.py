import os
import socket
import logging

logger = logging.getLogger(__name__)

try:
    from ddtrace import tracer, patch_all
    # Try both old and new import paths for FastAPI integration
    try:
        from ddtrace.contrib.fastapi import TraceMiddleware
    except ImportError:
        # For ddtrace v4+, use patch instead of middleware
        TraceMiddleware = None
    
    # Try to import HTTP writer for direct API submission
    try:
        from ddtrace.writer import AgentWriter, HTTPWriter
        HTTP_WRITER_AVAILABLE = True
    except ImportError:
        HTTP_WRITER_AVAILABLE = False
    
    DDTRACE_AVAILABLE = True
except ImportError as e:
    DDTRACE_AVAILABLE = False
    HTTP_WRITER_AVAILABLE = False
    print(f"Warning: ddtrace not available: {e}. Datadog tracing will be disabled.")

from fastapi import FastAPI


def _check_agent_connectivity(host: str, port: int, timeout: float = 2.0) -> bool:
    """
    Check if Datadog agent is reachable.
    Returns True if connection succeeds, False otherwise.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.debug(f"Failed to check Datadog agent connectivity: {e}")
        return False


def initialize_datadog_tracer(fastapi_app: FastAPI, service_name: str):
    """
    Initialize Datadog tracing for FastAPI without interfering with existing OTEL/Jaeger setup.
    """
    if not DDTRACE_AVAILABLE:
        logger.warning("Skipping Datadog tracer initialization - ddtrace not available")
        return

    try:
        # In ddtrace v4+, configuration is done via environment variables automatically
        # Set defaults if not already set in environment
        if not os.getenv("DD_SERVICE"):
            os.environ["DD_SERVICE"] = service_name
        if not os.getenv("DD_ENV"):
            # Set DD_ENV based on ENV variable (qa or prod), default to prod
            env_value = os.getenv("ENV", "prod").lower()
            if env_value == "qa":
                os.environ["DD_ENV"] = "qa"
            else:
                os.environ["DD_ENV"] = "prod"
        
        # Configure for direct API submission (not via agent)
        # Check if we should use direct API submission
        # Support both DD_TRACE_AGENT_URL and DD_APM_DD_URL as signals for direct API mode
        trace_agent_url = os.getenv("DD_TRACE_AGENT_URL") or os.getenv("DD_APM_DD_URL")
        agent_host = os.getenv("DD_AGENT_HOST")
        
        # Determine if we should use direct API submission
        # If trace agent URL is set OR agent host is not set, use direct API
        use_direct_api = trace_agent_url is not None or agent_host is None
        
        # Remove these env vars to prevent ddtrace from using them as agent URLs
        if os.getenv("DD_TRACE_AGENT_URL"):
            os.environ.pop("DD_TRACE_AGENT_URL", None)
        if os.getenv("DD_APM_DD_URL"):
            os.environ.pop("DD_APM_DD_URL", None)
        
        # Explicitly unset DD_AGENT_HOST if using direct API to prevent localhost fallback
        if use_direct_api and agent_host:
            logger.info(f"Unsetting DD_AGENT_HOST ({agent_host}) to use direct API submission")
            os.environ.pop("DD_AGENT_HOST", None)
            agent_host = None
        
        if use_direct_api:
            if not HTTP_WRITER_AVAILABLE:
                logger.error(
                    "HTTPWriter is not available in this ddtrace version. "
                    "Cannot use direct API submission. Please use agent mode or upgrade ddtrace."
                )
                # If no agent host and HTTPWriter unavailable, disable tracing to prevent localhost fallback
                if not agent_host:
                    logger.warning("Disabling Datadog tracing to prevent localhost fallback")
                    return
                use_direct_api = False
            else:
                # Direct API submission mode using HTTPWriter
                api_key = os.getenv("DD_API_KEY") or os.getenv("DATADOG_API_KEY")
                if not api_key:
                    logger.warning(
                        "DD_API_KEY or DATADOG_API_KEY not set. "
                        "Cannot use direct API submission. Falling back to agent mode or disabling traces."
                    )
                    use_direct_api = False
                    if not agent_host:
                        logger.warning("Disabling Datadog tracing to prevent localhost fallback")
                        return
                else:
                    # Determine the correct endpoint based on DD_SITE
                    dd_site = os.getenv("DD_SITE", "datadoghq.com")
                    if dd_site == "datadoghq.eu":
                        trace_url = "https://trace-intake.datadoghq.eu"
                    else:
                        trace_url = "https://trace-intake.datadoghq.com"
                    
                    try:
                        # Configure HTTPWriter for direct API submission
                        # HTTPWriter needs the API key for authentication
                        hostname_clean = trace_url.replace("https://", "").replace("http://", "")
                        logger.info(f"Attempting to configure HTTPWriter with hostname: {hostname_clean}, port: 443")
                        
                        http_writer = HTTPWriter(
                            hostname=hostname_clean,
                            port=443,
                            api_version="v0.4",  # Use v0.4 which is more stable
                            api_key=api_key,
                        )
                        # Configure the tracer with HTTPWriter BEFORE patch_all()
                        tracer.configure(writer=http_writer)
                        logger.info(f"Successfully configured Datadog tracer for direct API submission to: {trace_url}")
                    except Exception as e:
                        logger.error(f"Failed to configure HTTPWriter: {e}. Error type: {type(e).__name__}", exc_info=True)
                        use_direct_api = False
                        # If direct API fails and no agent host, disable tracing to avoid localhost fallback
                        if not agent_host:
                            logger.warning("Disabling Datadog tracing to prevent localhost fallback")
                            return
        
        if not use_direct_api and agent_host:
            # Agent-based mode
            agent_port = int(os.getenv("DD_TRACE_AGENT_PORT", "8126"))
            logger.info(f"Configuring Datadog tracer for agent-based submission to: {agent_host}:{agent_port}")
            
            # Check agent connectivity (optional, but helpful for debugging)
            if not _check_agent_connectivity(agent_host, agent_port):
                logger.warning(
                    f"Datadog agent at {agent_host}:{agent_port} appears unreachable. "
                    f"Traces may be dropped."
                )
            else:
                logger.info(f"Datadog agent at {agent_host}:{agent_port} is reachable")
        elif not use_direct_api:
            logger.warning(
                "No agent host or direct API configuration available. "
                "Traces will be collected but may not be sent."
            )
        
        # IMPORTANT: HTTPWriter must be configured BEFORE patch_all()
        # Now patch supported libraries automatically (requests, psycopg2, etc.)
        # For ddtrace v4+, this also patches FastAPI automatically
        patch_all()
        
        # Verify the writer configuration after patch_all()
        if use_direct_api:
            current_writer = getattr(tracer, 'writer', None)
            if current_writer:
                writer_type = type(current_writer).__name__
                logger.info(f"Current tracer writer type: {writer_type}")
                if writer_type != "HTTPWriter":
                    logger.warning(f"Expected HTTPWriter but got {writer_type}. Traces may not be sent correctly.")
            else:
                logger.warning("No writer configured on tracer. Traces may not be sent.")

        # For ddtrace < v4, use middleware if available
        if TraceMiddleware is not None:
            fastapi_app.add_middleware(TraceMiddleware, tracer=tracer)
            logger.info(f"Datadog tracer initialized for service: {service_name} (using middleware)")
        else:
            # For ddtrace v4+, FastAPI is auto-instrumented via patch_all()
            logger.info(f"Datadog tracer initialized for service: {service_name} (using patch_all)")

    except Exception as e:
        logger.error(f"Error initializing Datadog tracer: {e}. Continuing without Datadog tracing.", exc_info=True)
