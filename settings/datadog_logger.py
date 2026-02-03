import logging
import os
import json
import requests
import re

# =========================
# Datadog Configuration
# =========================

DATADOG_API_KEY = os.getenv("DATADOG_API_KEY")

# US1 site (correct for https://app.datadoghq.com)
DATADOG_LOG_URL = "https://http-intake.logs.datadoghq.com/v1/input"

# ONLY exclude very noisy internals
EXCLUDED_LOGGERS = {
    "multipart",   # file upload internals
    "httpcore",    # low-level HTTP noise
}

# Optional allowlist (comma-separated logger prefixes)
# Example: DD_INCLUDE_LOGGERS=etter_app,uvicorn.access
INCLUDE_LOGGERS = (
    os.getenv("DD_INCLUDE_LOGGERS").split(",")
    if os.getenv("DD_INCLUDE_LOGGERS")
    else None
)

# =========================
# Datadog Logging Handler
# =========================

class DatadogLogger(logging.Handler):
    def __init__(self, service: str):
        super().__init__()
        self.service = service
        self.env = os.getenv("ENV", "qa")

        # IMPORTANT:
        # Do NOT add timestamps / levels here
        # Uvicorn already formats access logs correctly
        self.setFormatter(logging.Formatter("%(message)s"))
        
        # Regex pattern to parse uvicorn access logs
        # Format: "IP:PORT - "METHOD PATH HTTP_VERSION" STATUS_CODE"
        # Example: "10.2.10.131:35054 - "GET /health HTTP/1.1" 200"
        self.access_log_pattern = re.compile(
            r'(\d+\.\d+\.\d+\.\d+):(\d+)\s+-\s+"(\w+)\s+([^\s?]+)(?:\?[^"]*)?\s+HTTP/[^"]+"\s+(\d+)'
        )

    def parse_access_log(self, message: str) -> dict:
        """
        Parse uvicorn access log to extract structured fields.
        Returns dict with http.method, http.url, http.status_code, etc.
        """
        match = self.access_log_pattern.match(message)
        if not match:
            return {}
        
        client_ip, client_port, method, path, status_code = match.groups()
        
        return {
            "http.method": method,
            "http.url": path,
            "http.status_code": int(status_code),
            "http.client_ip": client_ip,
            "http.client_port": int(client_port),
        }

    def should_log(self, record: logging.LogRecord) -> bool:
        """
        Decide whether to send this log to Datadog.
        """

        logger_name = record.name

        # Allowlist mode (if configured)
        if INCLUDE_LOGGERS:
            return any(
                logger_name.startswith(prefix.strip())
                for prefix in INCLUDE_LOGGERS
                if prefix.strip()
            )

        # Exclude only very noisy internal libraries
        for excluded in EXCLUDED_LOGGERS:
            if logger_name.startswith(excluded):
                return False

        # IMPORTANT:
        # Do NOT filter /health or access logs
        return True

    def emit(self, record: logging.LogRecord):
        if not DATADOG_API_KEY:
            return

        try:
            if not self.should_log(record):
                return

            message = record.getMessage()
            payload = {
                "message": message,
                "ddsource": "python",
                "service": self.service,
                "hostname": os.getenv("HOSTNAME"),
                "status": record.levelname.lower(),
                "ddtags": f"env:{self.env},service:{self.service}",
            }
            
            # Extract structured fields from LogRecord (set via extra= in logger calls)
            # Python logging adds extra fields directly as attributes on the LogRecord
            http_method = getattr(record, "http.method", None)
            http_url = getattr(record, "http.url", None)
            http_status = getattr(record, "http.status_code", None)
            event_type = getattr(record, "event_type", None)
            
            if http_method or http_url or http_status:
                # Add structured HTTP fields to payload
                if http_method:
                    payload["http.method"] = http_method
                if http_url:
                    payload["http.url"] = http_url
                if http_status:
                    payload["http.status_code"] = http_status
                if event_type:
                    payload["event_type"] = event_type
                
                # Add other extra fields that might be present
                for attr in dir(record):
                    if attr.startswith("http.") or attr in ["duration_ms", "http.client_ip", "http.client_port", "http.request_id"]:
                        value = getattr(record, attr, None)
                        if value is not None and attr not in payload:
                            payload[attr] = value
                
                # Build enhanced ddtags from structured fields
                tags = [f"env:{self.env}", f"service:{self.service}"]
                if http_method:
                    tags.append(f"http.method:{http_method.lower()}")
                if http_status:
                    tags.append(f"http.status_code:{http_status}")
                if event_type:
                    tags.append(f"event_type:{event_type}")
                
                payload["ddtags"] = ",".join(tags)
            
            # If this is a uvicorn access log, parse and add structured fields
            elif record.name == "uvicorn.access":
                http_fields = self.parse_access_log(message)
                if http_fields:
                    # Add structured fields to payload
                    payload.update(http_fields)
                    # Add method and status to ddtags for better filtering
                    method = http_fields.get("http.method", "").lower()
                    status = http_fields.get("http.status_code", "")
                    payload["ddtags"] += f",http.method:{method},http.status_code:{status}"
            
            # Add logger name for filtering
            payload["logger"] = record.name

            headers = {
                "Content-Type": "application/json",
                "DD-API-KEY": DATADOG_API_KEY,
            }

            requests.post(
                DATADOG_LOG_URL,
                headers=headers,
                data=json.dumps(payload),
                timeout=2,
            )

        except Exception:
            # Never break the app because of logging
            pass
