#!/bin/bash

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Voice Agent Portal - Turso Setup Script${NC}"
echo "This script will help you set up Turso for your application."
echo

# Check operating system
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    echo -e "${YELLOW}Warning: You are running on Windows.${NC}"
    echo -e "${YELLOW}The libsql-experimental package has known compatibility issues with Windows.${NC}"
    echo "Consider these options:"
    echo "1. Use WSL (Windows Subsystem for Linux) for development"
    echo "2. Use Docker for development (recommended)"
    echo "3. Deploy to a Linux-based cloud environment for production"
    echo
    echo -e "${YELLOW}For Docker users:${NC} The Dockerfile is already configured to work with Turso."
    echo -e "Continue with this script to set up your Turso database, but note that"
    echo -e "local testing outside of Docker may not work on Windows."
    echo
    read -p "Press Enter to continue or Ctrl+C to exit..."
fi

# Check if Turso CLI is installed
if ! command -v turso &> /dev/null; then
    echo -e "${RED}Turso CLI not found!${NC}"
    echo "Please install Turso CLI first by following the instructions at:"
    echo "https://docs.turso.tech/reference/turso-cli"
    echo
    echo "For macOS/Linux: curl -sSfL https://get.turso.tech | bash"
    echo "For Windows: Download the installer from https://turso.tech"
    exit 1
fi

echo -e "${GREEN}✓ Turso CLI is installed${NC}"

# Check if user is logged in
TURSO_AUTH_STATUS=$(turso auth status 2>&1)
if echo "$TURSO_AUTH_STATUS" | grep -q "not authenticated"; then
    echo -e "${RED}You are not authenticated with Turso${NC}"
    echo "Please login to Turso:"
    turso auth login
else
    echo -e "${GREEN}✓ You are authenticated with Turso${NC}"
fi

# Ask for database name
echo
echo "Enter a name for your Turso database (default: voice-agent-db):"
read DB_NAME
DB_NAME=${DB_NAME:-voice-agent-db}

# Check if database exists
DB_EXISTS=$(turso db list | grep "$DB_NAME" || echo "")
if [ -n "$DB_EXISTS" ]; then
    echo -e "${GREEN}✓ Database '$DB_NAME' already exists${NC}"
else
    echo "Creating database '$DB_NAME'..."
    turso db create "$DB_NAME"
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to create database${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Database created successfully${NC}"
fi

# Get database URL
echo "Getting database URL..."
DB_URL=$(turso db show "$DB_NAME" --url)
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to get database URL${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Got database URL${NC}"

# Create auth token
echo "Creating authentication token..."
AUTH_TOKEN=$(turso db tokens create "$DB_NAME")
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to create auth token${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Created authentication token${NC}"

# Update .env file
echo "Updating .env file..."
if [ ! -f .env ]; then
    cp .env.example .env 2>/dev/null || touch .env
fi

# Remove existing Turso entries if they exist
grep -v "TURSO_" .env > .env.tmp && mv .env.tmp .env

# Add Turso configuration
echo "# Turso Configuration" >> .env
echo "TURSO_DATABASE_URL=$DB_URL" >> .env
echo "TURSO_AUTH_TOKEN=$AUTH_TOKEN" >> .env

echo -e "${GREEN}✓ Environment variables set in .env file${NC}"

echo
echo -e "${BLUE}Setup complete!${NC}"
echo "Your Turso database is now configured to work with the Voice Agent Portal."
echo
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    echo -e "${YELLOW}Remember: On Windows, you should run the application using Docker:${NC}"
    echo "docker-compose up"
    echo
    echo -e "${YELLOW}If you need to develop locally outside Docker:${NC}"
    echo "1. Consider using WSL (Windows Subsystem for Linux)"
    echo "2. Or modify requirements.txt to use an alternate SQLite package"
else
    echo "To verify the setup, run: docker-compose up"
    echo "The application should now use Turso's distributed SQLite database."
fi 