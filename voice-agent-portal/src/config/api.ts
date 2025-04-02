// API Base URL
export const API_BASE_URL =
  process.env.REACT_APP_API_URL || "http://localhost:8000";

// Authentication endpoints
export const AUTH_ENDPOINTS = {
  ADMIN_LOGIN: "/api/auth/login/admin",
  OTP_LOGIN: "/api/auth/login/otp",
  CHANGE_PASSWORD: "/api/auth/change-password",
};

// OTP Management endpoints
export const OTP_ENDPOINTS = {
  LIST: "/api/otps/",
  CREATE: "/api/otps/",
  UPDATE: (id: string) => `/api/otps/${id}`,
  DELETE: (id: string) => `/api/otps/${id}`,
};

// OTP Request endpoints
export const OTP_REQUEST_ENDPOINTS = {
  CREATE: "/api/otp-requests/",
  LIST: "/api/otp-requests/admin",
  APPROVE: (id: string) => `/api/otp-requests/${id}/approve`,
  REJECT: (id: string) => `/api/otp-requests/${id}/reject`,
  DELETE: (id: string) => `/api/otp-requests/${id}/delete`,
};

// Agent endpoints
export const AGENT_ENDPOINTS = {
  LIST: "/api/agents/list",
  ACCESS: "/api/agents/access",
};

// Admin Agent endpoints
export const ADMIN_AGENT_ENDPOINTS = {
  LIST: "/api/admin/agents/",
  CREATE: "/api/admin/agents/",
  GET: (id: string) => `/api/admin/agents/${id}`,
  UPDATE: (id: string) => `/api/admin/agents/${id}`,
  DELETE: (id: string) => `/api/admin/agents/${id}`,
  ENABLE: (id: string) => `/api/admin/agents/${id}/enable`,
  DISABLE: (id: string) => `/api/admin/agents/${id}/disable`,
  SYSTEM_CONFIG: "/api/admin/agents/config/system",
  USAGE: "/api/admin/agents/usage",
  TRAFFIC: "/api/admin/agents/traffic",
  CLEAR_USAGE: "/api/admin/agents/usage/clear",
  CLEAR_TRAFFIC: "/api/admin/agents/traffic/clear",
};
