# Voice Agent Portal Backend

A FastAPI backend for a voice agent portal with OTP-based authentication system. This backend allows:

- Admin users to manage OTPs (create, update, delete)
- Regular users to login with OTPs and access voice agents
- Tracking agent usage and traffic
- Voice Agent integration with secure access control

## Setup and Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd voice-agent-portal-backend
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables (create or modify `.env` file):

```
SECRET_KEY=your-super-secret-key-change-this-in-production
DATABASE_URL=sqlite:///./app.db

# Voice agent configuration
CLAUDE_API_KEY=your-anthropic-claude-api-key
```

4. Run the application:

```bash
python run.py
```

The API will be available at `http://localhost:8000`

## Database Security

The backend includes enhanced security for the database:

- SQLite-specific security pragmas:

  - Foreign key constraints enabled
  - Secure deletion enabled
  - Memory mapping disabled to prevent exploits
  - Exclusive access mode to prevent race conditions

- For production databases (PostgreSQL, MySQL):
  - Connection pooling with limited pool size
  - Connection recycling
  - Connection timeout limits

## API Documentation

After starting the server, you can access the interactive API documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Authentication

The API uses JWT tokens for authentication. There are two types of users:

1. Admin users (username/password)
2. OTP users (6-digit code)

#### Endpoints

- `POST /api/auth/login/admin` - Admin login
- `POST /api/auth/login/otp` - OTP login

### OTP Management

- `GET /api/otps/` - Get all OTPs (admin only)
- `POST /api/otps/` - Generate new OTPs (admin only)
- `PUT /api/otps/{otp_id}` - Update OTP uses (admin only)
- `DELETE /api/otps/{otp_id}` - Delete OTP (admin only)

### Agent Access & Voice Agent Integration

- `GET /api/agents/list` - List all available agents
- `GET /api/agents/config/{agent_id}` - Get configuration for a specific agent
- `POST /api/agents/access` - Access an agent (decrements OTP uses)
- `GET /api/agents/usage` - Get agent usage history (admin only)
- `GET /api/agents/traffic` - Get agent traffic statistics (admin only)

### Voice Agent Streaming

- `GET /api/voice-agents/stream?agent_type={agent_type}` - WebSocket endpoint for voice agents
  - Where `{agent_type}` can be `realestate`, `hospital`, or any other configured agent

## Default Admin Account

The application creates a default admin account on startup:

- Username: `cawadmin`
- Password: `adminc@w`

This account is automatically created when you start the application. The credentials cannot be changed through the API - you would need to modify the code in `app/main.py` if you want different credentials.

## Voice Agent Integration

The backend integrates voice agents through a unified endpoint at `/api/voice-agents/stream` where the client can specify the desired agent type. Here's how it works:

1. Client first gets a list of available agents from `/api/agents/list`
2. User selects an agent type (e.g., "realestate" or "hospital")
3. Client calls `/api/agents/access` to register the usage and decrement OTP use
4. Client connects to `/api/voice-agents/stream?agent_type={selected_agent}` with authentication
5. The server dynamically selects the appropriate agent pipeline, startup message, and conversation context
6. Each user gets their own isolated conversation session that's tied to their authentication token and selected agent
7. Agent usage statistics are tracked for admin monitoring

### Voice Agent Implementation

The voice agents use:

- Speech-to-text service to convert user audio to text
- Claude API for natural language processing
- Text-to-speech service to convert responses back to audio
- FastRTC for real-time audio streaming

### Adding Your Own Voice Agents

To add new voice agents:

1. Update the `app/utils/agent_config.py` file with your agent configuration
2. Add your agent configuration to the `AGENT_CONFIGS` dictionary in `app/routers/voice_agents.py`
3. Ensure your agent's dependencies are added to the requirements.txt file

## React Frontend Integration

### Authentication Flow

1. **Admin Login**:

```javascript
// Example using axios
const loginAdmin = async (username, password) => {
  try {
    const response = await axios.post(
      "http://localhost:8000/api/auth/login/admin",
      new URLSearchParams({
        username: username,
        password: password,
      }),
      {
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      }
    );

    const { access_token } = response.data;

    // Store token in localStorage or state management
    localStorage.setItem("token", access_token);
    localStorage.setItem("userType", "admin");

    return true;
  } catch (error) {
    console.error("Login failed:", error);
    return false;
  }
};
```

2. **OTP Login**:

```javascript
// Example using fetch
const loginWithOTP = async (otpCode) => {
  try {
    const response = await fetch("http://localhost:8000/api/auth/login/otp", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        otp_code: otpCode,
      }),
    });

    if (!response.ok) {
      throw new Error("Invalid OTP");
    }

    const data = await response.json();

    // Store token in localStorage or state management
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("userType", "otp");
    localStorage.setItem("otpCode", otpCode);

    return true;
  } catch (error) {
    console.error("OTP login failed:", error);
    return false;
  }
};
```

### Voice Agent Integration in React

Here's how to connect to the voice agent WebSocket stream in your React application:

```javascript
import React, { useState, useEffect, useRef } from "react";
import { FastRTC } from "fastrtc";

// Component to list and select agents
const AgentSelection = ({ onSelect, token }) => {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/agents/list", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setAgents(data);
        }
      } catch (error) {
        console.error("Failed to fetch agents:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchAgents();
  }, [token]);

  if (loading) return <div>Loading available agents...</div>;

  return (
    <div className="agent-selection">
      <h2>Select an Agent</h2>
      <div className="agent-list">
        {agents.map((agent) => (
          <div
            key={agent.id}
            className="agent-card"
            onClick={() => onSelect(agent.id)}
          >
            <h3>{agent.name}</h3>
            <p>{agent.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

// Main voice agent component
const VoiceAgentPage = () => {
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const streamRef = useRef(null);
  const token = localStorage.getItem("token");

  const selectAgent = async (agentType) => {
    setIsConnecting(true);

    try {
      // First call /api/agents/access to decrement OTP use count
      await fetch("http://localhost:8000/api/agents/access", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          agent_type: agentType,
        }),
      });

      // Set the selected agent to trigger connection
      setSelectedAgent(agentType);
    } catch (error) {
      console.error("Failed to access agent:", error);
      setIsConnecting(false);
    }
  };

  useEffect(() => {
    // Connect to the selected agent when it changes
    if (selectedAgent && token) {
      connectToVoiceAgent(selectedAgent, token);
    }

    return () => {
      // Cleanup voice agent connection
      if (streamRef.current) {
        streamRef.current.close();
      }
    };
  }, [selectedAgent, token]);

  const connectToVoiceAgent = (agentType, token) => {
    // Create a FastRTC client instance with authentication
    const rtc = new FastRTC({
      url: `ws://localhost:8000/api/voice-agents/stream?agent_type=${agentType}`,
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    // Connect to the voice agent stream
    rtc.connect();

    // Set up event handlers
    rtc.onConnected(() => {
      console.log(`Connected to ${agentType} agent`);
      setIsConnecting(false);
    });

    rtc.onDisconnected(() => {
      console.log(`Disconnected from ${agentType} agent`);
    });

    rtc.onError((error) => {
      console.error("Voice agent error:", error);
      setIsConnecting(false);
    });

    // Store the reference for cleanup
    streamRef.current = rtc;
  };

  if (!selectedAgent) {
    return <AgentSelection onSelect={selectAgent} token={token} />;
  }

  return (
    <div>
      <h1>{selectedAgent.toUpperCase()} Voice Agent</h1>
      {isConnecting ? (
        <div>Connecting to agent...</div>
      ) : (
        <div>
          {/* Voice agent UI components */}
          <button onClick={() => setSelectedAgent(null)}>Change Agent</button>
        </div>
      )}
    </div>
  );
};

export default VoiceAgentPage;
```

### Admin Dashboard Integration

1. **Fetching OTPs for Admin**:

```javascript
const fetchOTPs = async () => {
  try {
    const response = await api.get("/otps");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch OTPs:", error);
    return [];
  }
};
```

2. **Generating New OTPs**:

```javascript
const generateOTPs = async (count = 1, maxUses = 5) => {
  try {
    const response = await api.post("/otps", {
      count: count,
      max_uses: maxUses,
    });
    return response.data;
  } catch (error) {
    console.error("Failed to generate OTPs:", error);
    return null;
  }
};
```

3. **Updating OTP Uses**:

```javascript
const updateOTP = async (otpId, maxUses) => {
  try {
    const response = await api.put(`/otps/${otpId}`, {
      max_uses: maxUses,
    });
    return response.data;
  } catch (error) {
    console.error("Failed to update OTP:", error);
    return null;
  }
};
```

4. **Fetching Agent Traffic Statistics**:

```javascript
const fetchAgentTraffic = async () => {
  try {
    const response = await api.get("/agents/traffic");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch agent traffic:", error);
    return [];
  }
};
```

## Security Considerations

1. **CORS**: The API has CORS restricted to specific origins. For production, update the allowed origins in `app/main.py`.
2. **Environment Variables**: Ensure sensitive data like the `SECRET_KEY` and API keys are stored in environment variables.
3. **HTTPS**: In production, ensure the API is served over HTTPS.
4. **Database Security**: The database configuration includes enhanced security measures.

## License

[Include license information]

## Authentication Endpoints

### Admin Login

- **Endpoint**: `/api/auth/login/admin`
- **Method**: POST
- **Description**: Authenticate as admin and receive a JWT token
- **Request Body**:

```json
{
  "username": "username",
  "password": "password"
}
```

- **Response**: JWT token

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Change Admin Password

- **Endpoint**: `/api/auth/change-password`
- **Method**: PUT
- **Description**: Change the admin password
- **Authentication**: Requires admin JWT token
- **Request Body**:

```json
{
  "current_password": "adminc@w",
  "new_password": "new_secure_password"
}
```

- **Response**: Success message

```json
{
  "message": "Password changed successfully"
}
```

### OTP Login

- **Endpoint**: `/api/auth/login/otp`
- **Method**: POST
- **Description**: Authenticate with a one-time password and receive a JWT token
- **Request Body**:

```json
{
  "otp_code": "123456"
}
```

- **Response**: JWT token

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```
