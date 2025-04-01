from app.main import app

# For WSGI servers (Gunicorn, uWSGI, etc.)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("wsgi:app", host="0.0.0.0", port=8000) 