from fastapi import FastAPI, HTTPException
from settings.service_tracer import initialize_tracer
from settings.datadog_tracer import initialize_datadog_tracer
from settings.datadog_logger import DatadogLogger
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from datetime import datetime
import logging
from api.s3.api.routes_documents import documents_router
from api.s3.api.routes_uploads import uploads_router
from api.s3.api.routes_filesystem import filesystem_router
from api.etter_apis import etter_api_router
from api.auth import auth_router
from api.user_management import user_management_router
from api.function_workflow_task_apis import function_workflow_task_router
from api.chatbot import chatbot_router
from api.extraction import extraction_router
from api.gateway import gateway_router
from etter_workflows.api import router as pipeline_router
from middleware.cors_middleware import add_cors_middleware
from middleware.datadog_logging_middleware import DatadogLoggingMiddleware

description = """
#### Etter APIs:  🚀
   Etter API's to handle all the client side requests and responses.
"""

etter_app = FastAPI(
    title="Etter",
    description=description,
    version="1.0.0",
    openapi_version="3.1.0",
    root_path="/api",
    docs_url="/docs/etter",
    terms_of_service="https://draup.com/privacy/",
)


@etter_app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "failure",
            "data": None,
            "errors": [exc.detail]
        }
    )

add_cors_middleware(etter_app)
etter_app.add_middleware(GZipMiddleware, minimum_size=1000)
# Add Datadog logging middleware for structured HTTP request logging
etter_app.add_middleware(DatadogLoggingMiddleware)

etter_app.include_router(etter_api_router)
etter_app.include_router(auth_router)
etter_app.include_router(user_management_router)
etter_app.include_router(function_workflow_task_router)

etter_app.include_router(documents_router)
etter_app.include_router(uploads_router)
etter_app.include_router(filesystem_router)
etter_app.include_router(chatbot_router)
etter_app.include_router(extraction_router)
etter_app.include_router(gateway_router)
etter_app.include_router(pipeline_router)

@etter_app.get('/')
def read_root():
    """
    Root endpoint to check if the Etter API is running.
    """
    return {"message": "Etter API is running successfully!"}

@etter_app.get('/health')
def health_check():
    """
    Lightweight health check endpoint for Kubernetes probes.
    This endpoint is designed to be fast and not affected by long-running requests.
    """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


service_name = "Etter"

# Initialize Jaeger tracer (existing)
initialize_tracer(service_name, etter_app)

# Initialize Datadog tracer (new)
initialize_datadog_tracer(etter_app, service_name)

# Setup Datadog logger (attach to ROOT logger and uvicorn.access)
dd_handler = DatadogLogger(service=service_name)
dd_handler.setLevel(logging.INFO)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(dd_handler)

# Ensure uvicorn.access logs propagate to root logger (no direct handler)
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.setLevel(logging.INFO)
uvicorn_access_logger.propagate = True

root_logger.info("🔥 Datadog root logger initialized")