// Backend server configuration
export const BACKEND_CONFIG = {
  // The base URL of the backend server
  baseUrl: process.env.REACT_APP_BACKEND_URL || "/api",
  API_URL: process.env.REACT_APP_API_URL || "/api",

  // WebSocket configuration
  wsProtocol: window.location.protocol === "https:" ? "wss:" : "ws:",

  // API endpoints
  endpoints: {
    agents: {
      list: "/api/agents/list",
      access: "/api/agents/access",
      usage: "/api/agents/usage",
      clearUsage: "/api/agents/usage/clear",
    },
    admin: {
      agents: "/api/admin/agents",
      systemConfig: "/api/admin/agents/config/system",
      otps: "/api/otps",
    },
    auth: {
      login: {
        admin: "/api/auth/login/admin",
        otp: "/api/auth/login/otp",
      },
      changePassword: "/api/auth/change-password",
    },
  },
};
