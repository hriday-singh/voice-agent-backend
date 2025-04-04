import uvicorn
import os

if __name__ == "__main__":
    os.environ["ENVIRONMENT"] = "production"
    
    # Start the server with hot reload enabled
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, workers=2)