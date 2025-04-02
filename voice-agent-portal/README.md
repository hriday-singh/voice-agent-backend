# Voice Agent Portal

A React-based frontend for interacting with AI voice agents via WebRTC. This application provides a user interface for connecting to and communicating with voice agents using real-time audio streaming.

## Features

- User authentication via OTP and admin login
- Selection of different AI voice agents
- Real-time audio communication with AI agents
- Transcript display of conversations
- Admin panel for OTP management

## Technologies Used

- React with TypeScript
- WebRTC for real-time audio streaming
- React Router for navigation
- Axios for API requests

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- Backend server running at `http://localhost:8000`

### Installation

1. Clone the repository
2. Install dependencies:

```bash
cd voice-agent-portal
npm install
```

3. Start the development server:

```bash
npm start
```

The application will be available at [http://localhost:3000](http://localhost:3000)

## Project Structure

```
src/
├── components/
│   ├── Admin/
│   │   ├── OTPManagement.tsx
│   │   └── Admin.css
│   ├── Auth/
│   │   ├── AdminLogin.tsx
│   │   ├── OTPLogin.tsx
│   │   └── Auth.css
│   └── VoiceAgent/
│       ├── AgentSelector.tsx
│       ├── VoiceAgentStream.tsx
│       ├── VoiceAgentPage.tsx
│       └── VoiceAgent.css
├── services/
│   ├── api.ts
│   ├── auth.ts
│   └── webrtc.ts
├── App.tsx
└── index.tsx
```

## Usage Instructions

### OTP Login

1. Navigate to `/login`
2. Enter the OTP code provided by an administrator
3. Click "Login" to access the voice agent selection page

### Admin Login

1. Navigate to `/admin/login`
2. Enter your admin credentials
3. Access the OTP management dashboard

### Voice Agent Interaction

1. After logging in, select a voice agent from the list
2. Allow microphone access when prompted
3. Click the microphone button to start speaking
4. View the conversation transcript in real-time

## WebRTC Integration

The voice agent communication is handled through WebRTC:

1. User microphone audio is captured and sent to the server
2. The AI agent processes the audio and responds
3. Audio from the AI agent is streamed back to the user
4. Real-time transcripts are displayed in the interface

## License

This project is licensed under the MIT License.
