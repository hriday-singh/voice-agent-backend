// API Base URL
export const API_BASE_URL = process.env.REACT_APP_API_URL || "/api";

// Authentication endpoints
export const AUTH_ENDPOINTS = {
  ADMIN_LOGIN: "/auth/login/admin",
  OTP_LOGIN: "/auth/login/otp",
  CHANGE_PASSWORD: "/auth/change-password",
};

// OTP Management endpoints
export const OTP_ENDPOINTS = {
  LIST: "/otps/",
  CREATE: "/otps/",
  UPDATE: (id: string) => `/otps/${id}`,
  DELETE: (id: string) => `/otps/${id}`,
};

// OTP Request endpoints
export const OTP_REQUEST_ENDPOINTS = {
  CREATE: "/otp-requests/",
  LIST: "/otp-requests/admin",
  APPROVE: (id: string) => `/otp-requests/${id}/approve`,
  REJECT: (id: string) => `/otp-requests/${id}/reject`,
  DELETE: (id: string) => `/otp-requests/${id}/delete`,
};

// Agent endpoints
export const AGENT_ENDPOINTS = {
  LIST: "/agents/list",
  ACCESS: "/agents/access",
};

// Admin Agent endpoints
export const ADMIN_AGENT_ENDPOINTS = {
  LIST: "/admin/agents/",
  CREATE: "/admin/agents/",
  GET: (id: string) => `/admin/agents/${id}`,
  UPDATE: (id: string) => `/admin/agents/${id}`,
  DELETE: (id: string) => `/admin/agents/${id}`,
  ENABLE: (id: string) => `/admin/agents/${id}/enable`,
  DISABLE: (id: string) => `/admin/agents/${id}/disable`,
  SYSTEM_CONFIG: "/admin/agents/config/system",
  USAGE: "/admin/agents/usage",
  TRAFFIC: "/admin/agents/traffic",
  CLEAR_USAGE: "/admin/agents/usage/clear",
  CLEAR_TRAFFIC: "/admin/agents/traffic/clear",
};
