# Turso Database Integration

This project supports [Turso](https://turso.tech/), a distributed SQLite database built on libSQL, designed for global deployments with low latency.

## Why Turso?

- **Edge Database**: Turso brings data closer to users with global distribution
- **SQLite Compatibility**: Uses the familiar SQLite interface and SQL syntax
- **Low Latency**: Provides lightning-fast read and write operations
- **Serverless**: Eliminates the need for database server management
- **Cost-effective**: Pay for what you use with a generous free tier

## Setup Options

### Automated Setup

For all platforms, use our setup script:

```bash
./setup_turso.sh
```

This script will:

1. Check if Turso CLI is installed
2. Verify authentication status
3. Create a new database (or use existing one)
4. Set up access credentials
5. Add environment variables to your `.env` file

### Manual Setup

1. Install the Turso CLI

   ```bash
   # macOS/Linux
   curl -sSfL https://get.turso.tech | bash
   # Windows: Download from website
   ```

2. Authenticate with Turso

   ```bash
   turso auth login
   ```

3. Create a database

   ```bash
   turso db create voice-agent-db
   ```

4. Get the database URL

   ```bash
   turso db show voice-agent-db --url
   ```

5. Create an auth token

   ```bash
   turso db tokens create voice-agent-db
   ```

6. Add to your `.env` file
   ```
   TURSO_DATABASE_URL=your_db_url
   TURSO_AUTH_TOKEN=your_auth_token
   ```

## Windows-Specific Information

Windows users may encounter compatibility issues with the libsql-experimental package. Please refer to [windows_turso_guide.md](./windows_turso_guide.md) for Windows-specific instructions.

## Docker Integration

When using Docker, the Turso database works seamlessly as the container is Linux-based. The docker-compose.yml is configured to read Turso environment variables from your `.env` file.

## Fallback to Local SQLite

The application will automatically fall back to a local SQLite database if:

- Turso credentials are not configured
- Running on Windows without forcing Turso (due to compatibility issues)
- The `TURSO_FORCE_LOCAL` environment variable is set to `true`

## Development vs. Production

For local development, you may want to use a local SQLite database. For production, using Turso is recommended for better performance and reliability.

## Troubleshooting

If you encounter database connection issues:

1. Verify your Turso credentials are correct
2. Check your database permissions
3. For Windows users, consider using Docker or WSL
4. Examine application logs for specific error messages

## Resources

- [Turso Documentation](https://docs.turso.tech/)
- [libSQL on GitHub](https://github.com/tursodatabase/libsql)
- [SQLAlchemy libSQL Dialect](https://github.com/libsql/sqlalchemy-libsql)
