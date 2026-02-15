import logging
import uvicorn

# Ensure provider / streaming logs are visible
logging.basicConfig(level=logging.INFO)
for name in ("core.llm.providers", "app.socket_handler", "core.llm.session_manager"):
    logging.getLogger(name).setLevel(logging.INFO)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",    
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False      
    )
