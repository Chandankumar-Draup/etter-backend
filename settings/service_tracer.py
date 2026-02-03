import logging
import os
import re
from typing import Any, Dict
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.trace import Span
import json

logger = logging.getLogger('location-logger')

def initialize_tracer(
        service_name, fastapi_app,
        jaeger_host='jaeger-agent.jaeger.svc.cluster.local', jaeger_port=6831
):
    trace.set_tracer_provider(
        TracerProvider(
            resource=Resource.create({SERVICE_NAME: service_name})
        )
    )
    tracer = trace.get_tracer(__name__)

    # create a JaegerExporter
    jaeger_exporter = JaegerExporter(
        # configure agent
        agent_host_name=jaeger_host,
        agent_port=jaeger_port,
    )
    # Create a BatchSpanProcessor and add the exporter to it
    span_processor = BatchSpanProcessor(jaeger_exporter)

    tracer_provider = trace.get_tracer_provider()
    # add to the tracer
    tracer_provider.add_span_processor(span_processor)

    # --- Hooks to capture payloads ---
    def server_request_hook(span: Span, scope: Dict[str, Any]) -> None:
        if span and span.is_recording():
            # ASGI scope is available here; request body is not.
            # Capture safe, non-blocking attributes only.
            try:
                query_string = scope.get("query_string")
                if query_string:
                    if isinstance(query_string, (bytes, bytearray)):
                        qs_value = query_string[:2048].decode("utf-8", errors="replace")
                    else:
                        qs_value = str(query_string)[:2048]
                    span.set_attribute("http.request.query_string", qs_value)
            except Exception:
                pass

    def client_response_hook(span: Span, scope: Dict[str, Any], message: Dict[str, Any]) -> None:
        if span and span.is_recording():
            # Only capture response body for http responses
            try:
                body = message.get("body") if isinstance(message, dict) else None
                if body:
                    # Limit body size for tracing
                    span.set_attribute("http.response.body", body[:2048].decode("utf-8", errors="replace"))
            except Exception:
                pass

    # Instrument FastAPI with header capture and hooks
    # Remove all sanitization of headers
    sanitize_fields: list[str] = []
    os.environ.setdefault("OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SANITIZE_FIELDS", "")
    # Exclude both /health and /api/health
    excluded_health_regex = r"^(?:/api)?/health(?:$|/.*)"
    # Set env-based exclusions too (some versions prefer env configuration)
    os.environ.setdefault("OTEL_PYTHON_FASTAPI_EXCLUDED_URLS", excluded_health_regex)
    os.environ.setdefault("OTEL_PYTHON_STARLETTE_EXCLUDED_URLS", excluded_health_regex)
    FastAPIInstrumentor().instrument_app(
        fastapi_app,
        tracer_provider=tracer_provider,
        server_request_hook=server_request_hook,
        client_response_hook=client_response_hook,
        http_capture_headers_server_request=[".*"],
        http_capture_headers_server_response=[".*"],
        http_capture_headers_sanitize_fields=sanitize_fields,
        excluded_urls=excluded_health_regex,
    )

    # ASGI middleware to capture request body and headers safely
    from opentelemetry.instrumentation.utils import suppress_instrumentation

    class OTelRequestBodyCaptureMiddleware:
        def __init__(self, app, max_bytes: int = 2048, sanitize: list[str] | None = None):
            self.app = app
            self.max_bytes = max_bytes
            self.sanitize = set([s.lower() for s in (sanitize or [])])
            self.health_pattern = re.compile(excluded_health_regex)

        async def __call__(self, scope, receive, send):
            if scope.get("type") != "http":
                await self.app(scope, receive, send)
                return
            # Skip health endpoints entirely (supports optional root_path like /api)
            path = scope.get("path") or ""
            root_path = scope.get("root_path") or ""
            effective_path = f"{root_path}{path}"
            if self.health_pattern.match(path) or self.health_pattern.match(effective_path):
                # Suppress all instrumentation within this request
                with suppress_instrumentation():
                    await self.app(scope, receive, send)
                return

            body_chunks = bytearray()
            # Capture and set headers early while span is active
            try:
                span = trace.get_current_span()
                if span and span.is_recording():
                    headers_list = scope.get("headers") or []
                    headers_dict = {}
                    for k_b, v_b in headers_list:
                        key = k_b.decode("latin-1", "replace")
                        value = v_b.decode("latin-1", "replace")
                        if key.lower() in self.sanitize:
                            headers_dict[key] = "[REDACTED]"
                        else:
                            headers_dict[key] = value
                    headers_json = json.dumps(headers_dict)
                    span.set_attribute("http.request.headers", headers_json[: self.max_bytes])
            except Exception:
                pass

            async def receive_wrapper():
                message = await receive()
                if message.get("type") == "http.request":
                    chunk = message.get("body", b"")
                    if chunk:
                        body_chunks.extend(chunk)
                    # If this is the last chunk, set attribute immediately
                    try:
                        if not message.get("more_body", False):
                            span_local = trace.get_current_span()
                            if span_local and span_local.is_recording() and body_chunks:
                                span_local.set_attribute(
                                    "http.request.body",
                                    bytes(body_chunks)[: self.max_bytes].decode("utf-8", errors="replace"),
                                )
                    except Exception:
                        pass
                return message

            try:
                await self.app(scope, receive_wrapper, send)
            except Exception as e:
                pass

    # Add middleware after instrumentation so it runs within the active span context
    fastapi_app.add_middleware(
        OTelRequestBodyCaptureMiddleware,
        max_bytes=2048,
        sanitize=sanitize_fields,
    )
    logger.info(f"Tracer Initialized for - \n {service_name}:{jaeger_host}: {jaeger_port}")