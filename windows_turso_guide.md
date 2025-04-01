# Turso Setup Guide for Windows Users

## Known Issues

Windows users may encounter challenges when working with Turso SQLite (libsql) due to the library's compatibility issues on Windows. The primary package `libsql-experimental` that provides native bindings often fails to compile on Windows systems.

## Recommended Solutions

### 1. Use Docker (Recommended)

The simplest solution is to use Docker for development and deployment:

```bash
# Set up Turso database
./setup_turso.sh

# Run the application in Docker
docker-compose up
```

With this approach, you:

- Don't need to worry about Windows compatibility issues
- Get an environment identical to production
- Can use Turso's distributed SQLite database seamlessly

### 2. Use Windows Subsystem for Linux (WSL)

If you prefer native development:

1. [Install WSL](https://learn.microsoft.com/en-us/windows/wsl/install)
2. Open your project in WSL
3. Run the setup script in the WSL environment:
   ```bash
   ./setup_turso.sh
   ```
4. Develop and test within WSL

### 3. Local Windows Development with Fallback

If you need to develop outside Docker/WSL on Windows:

1. Run the `setup_turso.sh` script to create your Turso database
2. Add this to your `.env` file:
   ```
   # Force local SQLite fallback
   TURSO_FORCE_LOCAL=true
   ```
3. When running on Windows, the application will automatically fall back to local SQLite

## Advanced: SQLAlchemy URL Structure

The application is configured to check for Turso credentials and fall back to local SQLite if needed.

The database configuration logic:

1. Checks for `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN`
2. If both are present and not on Windows (or if forced with `TURSO_FORCE_LOCAL`), uses Turso
3. Otherwise, falls back to local SQLite

## Need Help?

If you encounter issues:

1. Verify your Turso credentials are correct
2. Try running with Docker using `docker-compose up`
3. Check the logs for specific database connection errors
