import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "settings.server:etter_app",
        host="0.0.0.0",
        port=7071,
        timeout_keep_alive=600,  # 10 minutes - longer than max request time
        timeout_graceful_shutdown=300,  # 5 minutes
        reload=False
    )