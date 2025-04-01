# Voice Agent Portal Backend

A FastAPI backend for a voice agent portal with OTP-based authentication system. This system provides AI voice agents for real estate and healthcare domains with secure access control.

## Features

- **OTP-based Authentication**: Secure one-time password system for user access
- **Admin Management Portal**: Admin interface to manage OTPs and monitor usage
- **Voice Agent Integration**: Real-time voice agents powered by Claude AI
- **Real-time Audio Streaming**: Using FastRTC for high-quality audio communication
- **Role-based Access Control**: Different access levels for admins and users
- **Usage Analytics**: Track and monitor agent usage and traffic
- **Secure Database Design**: With SQLite or Turso database options

## Technology Stack

- **Backend**: FastAPI (Python 3.8+)
- **Database**: SQLite (development) / Turso (production)
- **Authentication**: JWT tokens + OTP system
- **AI Integration**: Claude API (Anthropic)
- **Audio Streaming**: FastRTC
- **Speech Services**: Google Cloud Speech-to-Text, Text-to-Speech, ElevenLabs
- **Deployment**: Docker, Docker Compose

## Project Structure

```
voice-agent-portal-backend/
├── app/
│   ├── database/         # Database models and connection
│   ├── models/           # Data models
│   ├── routers/          # API endpoints
│   ├── schemas/          # Pydantic schemas
│   └── utils/            # Utility functions and agents
├── data/                 # Database files (gitignored)
├── tests/                # Test suite
├── .env                  # Environment variables (example provided)
├── .gitignore            # Git ignore file
├── docker-compose.yml    # Docker compose configuration
├── Dockerfile            # Docker build file
├── requirements.txt      # Python dependencies
└── run.py                # Application entry point
```

## Setup and Installation

### Local Development Setup

#### Prerequisites

- Python 3.8+
- pip package manager

#### Installation Steps

1. Clone the repository:

```bash
git clone <repository-url>
cd voice-agent-portal-backend
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up environment variables by creating a `.env` file:

```
# Required environment variables
SECRET_KEY=your-super-secret-key-change-this
DATABASE_URL=sqlite:///./data/app.db

# API Keys
CLAUDE_API_KEY=your-anthropic-claude-api-key
GOOGLE_APPLICATION_CREDENTIALS=path/to/google-credentials.json
ELEVENLABS_API_KEY=your-elevenlabs-api-key

# Optional - Turso Database
# TURSO_DATABASE_URL=libsql://your-database-url
# TURSO_AUTH_TOKEN=your-auth-token

# Deployment settings
ENVIRONMENT=development  # or production
FRONTEND_URL=http://localhost:3000
```

5. Run the application:

```bash
python run.py
```

The API will be available at `http://localhost:8000`

### Docker Setup

1. Build and run with Docker Compose:

```bash
docker-compose up -d
```

2. For production deployments:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Database Configuration

### SQLite (Default Development Database)

The application uses SQLite by default for development. The database file is stored in `data/app.db`.

### Turso Database (Recommended for Production)

For production, we recommend using Turso database:

1. Create a Turso account and database
2. Update your `.env` file with Turso credentials:

```
TURSO_DATABASE_URL=libsql://your-database-url
TURSO_AUTH_TOKEN=your-auth-token
```

## API Documentation

After starting the server, you can access the interactive API documentation at:

- Swagger UI: `http://localhost:8000/api/docs` (only in development mode)

### Core Endpoints

#### Authentication

- `POST /api/auth/login/admin` - Admin login
- `POST /api/auth/login/otp` - OTP login

#### OTP Management

- `GET /api/otps/` - Get all OTPs (admin only)
- `POST /api/otps/` - Generate new OTPs (admin only)
- `PUT /api/otps/{otp_id}` - Update OTP uses (admin only)
- `DELETE /api/otps/{otp_id}` - Delete OTP (admin only)

#### Agent Access

- `GET /api/agents/list` - List all available agents
- `GET /api/agents/config/{agent_id}` - Get configuration for a specific agent
- `POST /api/agents/access` - Access an agent (decrements OTP uses)
- `GET /api/agents/usage` - Get agent usage history (admin only)
- `GET /api/agents/traffic` - Get agent traffic statistics (admin only)

#### Voice Agent Streaming

- `GET /api/voice-agents/realestate` - WebSocket endpoint for real estate agent
- `GET /api/voice-agents/hospital` - WebSocket endpoint for hospital agent

## Default Admin Account

The application creates a default admin account on startup:

- Username: `username`
- Password: `password`

This account is automatically created when you start the application.

## Security Features

The backend implements several security features:

- JWT token authentication with short expiration
- Strict CORS policy to prevent cross-origin attacks
- Security headers to protect against XSS and other attacks
- Hashed and salted passwords
- Rate limiting to prevent brute force attacks
- SQL injection protection through SQLAlchemy ORM
- Input validation with Pydantic

## Troubleshooting

### Common Issues

#### LibSQL Installation Issues

If you encounter issues installing the libsql-experimental package:

1. Ensure you have Rust installed:

   ```bash
   rustc --version
   ```

   If not installed, visit https://rustup.rs/ to install it.

2. For Windows users, ensure you have the Microsoft C++ Build Tools installed.

3. Alternative approach: Use SQLite driver instead:
   ```bash
   # In your .env file, use SQLite
   DATABASE_URL=sqlite:///./data/app.db
   # Comment out the Turso settings
   ```

#### Memory/Connection Issues

If encountering memory issues with voice agents:

1. Adjust memory optimization parameters in `app/utils/agents/agent_config.py`
2. Check connection limits in stream configurations

### Database Migration Issues

If encountering database migration issues:

1. Delete the existing database file (if using SQLite)
2. Run the application to recreate the database schema

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.

## Acknowledgments

- Anthropic for Claude AI API
- FastAPI for the amazing web framework
- FastRTC for the real-time audio streaming capabilities
- SQLAlchemy for the ORM functionality
- Turso for the distributed database solution
