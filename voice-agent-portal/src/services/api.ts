import axios, { AxiosInstance, InternalAxiosRequestConfig } from "axios";
import {
  API_BASE_URL,
  AUTH_ENDPOINTS,
  OTP_ENDPOINTS,
  OTP_REQUEST_ENDPOINTS,
  AGENT_ENDPOINTS,
  ADMIN_AGENT_ENDPOINTS,
  LLM_ENDPOINTS,
} from "../config/api";

// Create API instance with base URL and credentials
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

// Add token to all requests
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: any) => Promise.reject(error)
);

// Helper function to get error message
const getErrorMessage = (error: any): string => {
  return error.response?.data?.detail || error.message || "An error occurred";
};

// OTP Request interface
export interface OTPRequestForm {
  name: string;
  email: string;
  phoneNumber: string;
  purpose: string;
  company?: string;
}

// OTP Request response interface
export interface OTPRequestResponse {
  request_id: string;
  message: string;
  status: string;
}

// OTP Login response interface
export interface OTPLoginResponse {
  access_token: string;
  expires_in: number;
  remaining_uses: number;
}

// OTP interfaces
export interface OTP {
  id: number;
  code: string;
  max_uses: number;
  remaining_uses: number;
  description: string | null;
  created_at: string;
}

export interface OTPListResponse {
  data: OTP[];
  total: number;
  page: number;
  limit: number;
}

// OTP Request List Response interface
export interface OTPRequest {
  id: string;
  name: string;
  email: string;
  phone_number: string;
  purpose: string;
  company: string | null;
  status: string;
  created_at: string;
  ip_address: string;
}

export interface OTPRequestListResponse {
  data: OTPRequest[];
  total: number;
  page: number;
  limit: number;
}

// Admin OTP Management functions
export const fetchOTPList = async (page = 1, limit = 10): Promise<OTP[]> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.get(`${OTP_ENDPOINTS.LIST}`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    return response.data;
  } catch (error: any) {
    console.error("Failed to fetch OTPs:", error);
    throw new Error(getErrorMessage(error));
  }
};

export const generateOTPs = async (
  count: number,
  maxUses: number,
  description?: string
): Promise<{
  success: boolean;
  message?: string;
  error?: string;
  data?: OTP[];
}> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.post(
      OTP_ENDPOINTS.CREATE,
      {
        code: "", // Server will generate the code
        max_uses: maxUses,
        remaining_uses: 0,
        description: description || "",
        count: count,
      },
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    return {
      success: true,
      message: "OTPs generated successfully",
      data: response.data,
    };
  } catch (error: any) {
    console.error("Failed to generate OTPs:", error);
    return {
      success: false,
      error: getErrorMessage(error),
    };
  }
};

export const updateOTP = async (
  otpId: string,
  maxUses: number
): Promise<{
  success: boolean;
  message?: string;
  error?: string;
  data?: OTP;
}> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.put(
      OTP_ENDPOINTS.UPDATE(otpId),
      {
        max_uses: maxUses,
      },
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    return {
      success: true,
      message: "OTP updated successfully",
      data: response.data,
    };
  } catch (error: any) {
    return {
      success: false,
      error: getErrorMessage(error),
    };
  }
};

export const deleteOTP = async (
  otpId: string
): Promise<{ success: boolean; message?: string; error?: string }> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    await api.delete(OTP_ENDPOINTS.DELETE(otpId), {
      headers: { Authorization: `Bearer ${token}` },
    });

    return {
      success: true,
      message: "OTP deleted successfully",
    };
  } catch (error: any) {
    return {
      success: false,
      error: getErrorMessage(error),
    };
  }
};

// Request an OTP
export const requestOTP = async (
  formData: OTPRequestForm
): Promise<OTPRequestResponse> => {
  try {
    const response = await api.post(OTP_REQUEST_ENDPOINTS.CREATE, {
      name: formData.name,
      email: formData.email,
      phone_number: formData.phoneNumber,
      purpose: formData.purpose,
      company: formData.company || null,
    });

    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

// Login with OTP
export const loginWithOTP = async (
  otpCode: string
): Promise<{
  success: boolean;
  token?: string;
  expiresIn?: number;
  remainingUses?: number;
  error?: string;
}> => {
  try {
    const response = await api.post(AUTH_ENDPOINTS.OTP_LOGIN, {
      otp_code: otpCode,
    });

    localStorage.setItem("token", response.data.access_token);

    return {
      success: true,
      token: response.data.access_token,
      expiresIn: response.data.expires_in,
      remainingUses: response.data.remaining_uses,
    };
  } catch (error: any) {
    return {
      success: false,
      error: getErrorMessage(error),
    };
  }
};

// Access a voice agent
export const accessVoiceAgent = async (
  agentType: string
): Promise<{
  success: boolean;
  message?: string;
  remainingUses?: number;
  error?: string;
  agent_info?: {
    is_outbound: boolean;
    limitations: string[];
    primary_language: string;
    supported_languages: string[];
  };
}> => {
  try {
    const token = localStorage.getItem("token");
    if (!token) {
      return {
        success: false,
        error: "Not authenticated",
      };
    }

    const response = await api.post(
      AGENT_ENDPOINTS.ACCESS,
      { agent_type: agentType },
      { headers: { Authorization: `Bearer ${token}` } }
    );

    return {
      success: true,
      message: response.data.message,
      remainingUses: response.data.remaining_uses,
      agent_info: response.data.agent_info,
    };
  } catch (error: any) {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      return {
        success: false,
        error: "OTP is no longer valid. Please request a new one.",
      };
    }
    return {
      success: false,
      error: error.response?.data?.detail || "Failed to access voice agent",
    };
  }
};

// Connect to a voice agent (decrements OTP uses)
export const connectVoiceAgent = async (
  agentType: string
): Promise<{
  success: boolean;
  message?: string;
  remainingUses?: number;
  error?: string;
}> => {
  try {
    const token = localStorage.getItem("token");
    if (!token) {
      return {
        success: false,
        error: "Not authenticated",
      };
    }

    const response = await api.post(
      AGENT_ENDPOINTS.CONNECT,
      { agent_type: agentType },
      { headers: { Authorization: `Bearer ${token}` } }
    );

    return {
      success: true,
      message: response.data.message,
      remainingUses: response.data.remaining_uses,
    };
  } catch (error: any) {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      return {
        success: false,
        error: "OTP is no longer valid. Please request a new one.",
      };
    }
    return {
      success: false,
      error: error.response?.data?.detail || "Failed to connect to voice agent",
    };
  }
};

// Fetch OTP requests (admin only)
export const fetchOTPRequests = async (
  status: string | null = null,
  page = 1,
  limit = 10
): Promise<OTPRequestListResponse> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    let url = `${OTP_REQUEST_ENDPOINTS.LIST}?skip=${
      (page - 1) * limit
    }&limit=${limit}`;
    if (status) {
      url += `&status=${status}`;
    }

    const response = await api.get(url, {
      headers: { Authorization: `Bearer ${token}` },
    });

    // Handle both array and paginated object responses
    if (Array.isArray(response.data)) {
      return {
        data: response.data,
        total: response.data.length,
        page: 1,
        limit: response.data.length,
      };
    }

    return response.data;
  } catch (error: any) {
    console.error("Failed to fetch OTP requests:", error);
    throw new Error(getErrorMessage(error));
  }
};

// Approve OTP request (admin only)
export const approveOTPRequest = async (requestId: string) => {
  try {
    const token = localStorage.getItem("adminToken");

    const response = await api.post(
      OTP_REQUEST_ENDPOINTS.APPROVE(requestId),
      {},
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    // Handle both response formats
    if (typeof response.data === "string") {
      return {
        success: true,
        otp: response.data,
      };
    }

    // If response is an object with otp field
    if (response.data && response.data.otp) {
      return {
        success: true,
        otp: response.data.otp,
      };
    }

    // If response has a message field
    if (response.data && response.data.message) {
      return {
        success: true,
        otp: response.data.message,
      };
    }

    throw new Error("Invalid response format");
  } catch (error: any) {
    console.error("Error approving OTP request:", error);
    return {
      success: false,
      error: getErrorMessage(error),
    };
  }
};

// Reject OTP request (admin only)
export const rejectOTPRequest = async (requestId: string, reason: string) => {
  try {
    const token = localStorage.getItem("adminToken");

    const response = await api.post(
      OTP_REQUEST_ENDPOINTS.REJECT(requestId),
      { reason },
      { headers: { Authorization: `Bearer ${token}` } }
    );

    return {
      success: true,
      message: response.data.message,
    };
  } catch (error: any) {
    return {
      success: false,
      error: getErrorMessage(error),
    };
  }
};

// Change admin password
export const changeAdminPassword = async (
  currentPassword: string,
  newPassword: string
): Promise<{ success: boolean; message?: string; error?: string }> => {
  try {
    const token = localStorage.getItem("adminToken");

    if (!token) {
      return {
        success: false,
        error: "Not authenticated as admin",
      };
    }

    const response = await api.put(
      AUTH_ENDPOINTS.CHANGE_PASSWORD,
      {
        current_password: currentPassword,
        new_password: newPassword,
      },
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    return {
      success: true,
      message: response.data.message || "Password changed successfully",
    };
  } catch (error: any) {
    let errorMessage = "Failed to change password";

    if (error.response) {
      if (error.response.status === 401) {
        errorMessage = "Current password is incorrect";
      } else if (error.response.status === 403) {
        errorMessage = "You must be an admin to change password";
      } else if (error.response.status === 400) {
        errorMessage = error.response.data?.detail || "Invalid password format";
      }
    }

    return {
      success: false,
      error: errorMessage,
    };
  }
};

// Agent Management Functions
export interface Agent {
  id: number;
  agent_type: string;
  name: string;
  description: string;
  enabled: boolean;
  is_outbound: boolean;
  tags: string[];
}

export interface AgentDetail {
  id: number;
  name: string;
  description: string;
  agent_type: string;
  startup_message: string;
  system_prompt: string;
  can_interrupt: boolean;
  is_outbound: boolean;
  enabled: boolean;
  languages: {
    primary: string;
    supported: string[];
  };
  error_messages: {
    error: string;
    unclear_audio: string;
    unsupported_language: string;
  };
  limitations: string[];
  llm_model_id?: number;
  temperature?: number;
  speech_context: string[];
  tags: string[];
}

export interface UsageRecord {
  id: number;
  otp_id: number;
  agent_type: string;
  timestamp: string;
}

export interface UsageParams {
  limit?: number;
  offset?: number;
}

export const fetchAgentList = async (): Promise<any> => {
  try {
    const response = await api.get(AGENT_ENDPOINTS.LIST);
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

// Admin Agent Management Functions
export const fetchAllAgents = async (): Promise<Agent[]> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.get(ADMIN_AGENT_ENDPOINTS.LIST, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export const createAgent = async (
  agentData: AgentDetail
): Promise<AgentDetail> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    console.log(
      "Creating agent with data:",
      JSON.stringify(agentData, null, 2)
    );
    console.log("API Endpoint:", ADMIN_AGENT_ENDPOINTS.CREATE);

    const response = await api.post(ADMIN_AGENT_ENDPOINTS.CREATE, agentData, {
      headers: { Authorization: `Bearer ${token}` },
    });

    console.log("Agent creation successful, response:", response.data);
    return response.data;
  } catch (error: any) {
    console.error("Agent creation failed:", error);
    console.error("Error details:", error.response?.data || error.message);
    throw new Error(getErrorMessage(error));
  }
};

export const getAgent = async (agentId: string): Promise<AgentDetail> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.get(ADMIN_AGENT_ENDPOINTS.GET(agentId), {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export const updateAgent = async (
  agentId: string,
  agentData: Partial<AgentDetail>
): Promise<AgentDetail> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.put(
      ADMIN_AGENT_ENDPOINTS.UPDATE(agentId),
      agentData,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export const deleteAgent = async (
  agentId: string
): Promise<{ message: string }> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.delete(ADMIN_AGENT_ENDPOINTS.DELETE(agentId), {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export const enableAgent = async (
  agentId: string
): Promise<{ message: string }> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.put(
      ADMIN_AGENT_ENDPOINTS.ENABLE(agentId),
      {},
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export const disableAgent = async (
  agentId: string
): Promise<{ message: string }> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.put(
      ADMIN_AGENT_ENDPOINTS.DISABLE(agentId),
      {},
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export interface UsageResponse {
  data: UsageRecord[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}

export const getAgentUsage = async (
  params: UsageParams = { limit: 100, offset: 0 }
): Promise<UsageResponse> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const queryParams = new URLSearchParams({
      limit: params.limit?.toString() || "100",
      offset: params.offset?.toString() || "0",
    });

    const response = await api.get(
      `${ADMIN_AGENT_ENDPOINTS.USAGE}?${queryParams.toString()}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export const clearAgentUsage = async (): Promise<{
  success: boolean;
  message: string;
}> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.delete(ADMIN_AGENT_ENDPOINTS.CLEAR_USAGE, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

// LLM Provider and Model Interfaces
export interface LLMProvider {
  id: number;
  name: string;
  description: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface LLMModel {
  id: number;
  provider_id: number;
  name: string;
  display_name: string;
  default_temperature: number;
  created_at: string;
  updated_at: string;
  provider?: LLMProvider;
}

export interface LLMModelList {
  id: number;
  provider_id: number;
  name: string;
  display_name: string;
  default_temperature: number;
  created_at: string;
  updated_at: string;
  provider_name: string;
}

export interface LLMProviderCreate {
  name: string;
  description: string;
  enabled?: boolean;
}

export interface LLMModelCreate {
  provider_id: number;
  name: string;
  display_name: string;
  default_temperature: number;
}

// LLM Provider functions
export const fetchLLMProviders = async (): Promise<LLMProvider[]> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.get(LLM_ENDPOINTS.PROVIDERS_LIST, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export const createLLMProvider = async (
  provider: LLMProviderCreate
): Promise<{ id: number; message: string }> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.post(LLM_ENDPOINTS.PROVIDER_CREATE, provider, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export const updateLLMProvider = async (
  id: number,
  provider: Partial<LLMProviderCreate>
): Promise<{ message: string }> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.put(
      LLM_ENDPOINTS.PROVIDER_UPDATE(id),
      provider,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export const deleteLLMProvider = async (
  id: number
): Promise<{ message: string }> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.delete(LLM_ENDPOINTS.PROVIDER_DELETE(id), {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

// LLM Model functions
export const fetchLLMModels = async (
  providerId?: number
): Promise<LLMModel[]> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const url = providerId
      ? `${LLM_ENDPOINTS.MODELS_LIST}?provider_id=${providerId}`
      : LLM_ENDPOINTS.MODELS_LIST;

    const response = await api.get(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export const fetchLLMModelsList = async (): Promise<LLMModelList[]> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const url = LLM_ENDPOINTS.MODELS_LIST;

    const response = await api.get(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export const createLLMModel = async (
  model: LLMModelCreate
): Promise<{ id: number; message: string }> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.post(LLM_ENDPOINTS.MODEL_CREATE, model, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export const updateLLMModel = async (
  id: number,
  model: Partial<LLMModelCreate>
): Promise<{ message: string }> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.put(LLM_ENDPOINTS.MODEL_UPDATE(id), model, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export const deleteLLMModel = async (
  id: number
): Promise<{ message: string }> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.delete(LLM_ENDPOINTS.MODEL_DELETE(id), {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export interface LanguageCodes {
  [key: string]: string;
}

export interface VoiceConfig {
  [key: string]: {
    language_code: string;
    voice_name: string;
  };
}

export const getLanguageCodes = async (): Promise<LanguageCodes> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.get(ADMIN_AGENT_ENDPOINTS.LANGUAGE_CODES, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export const getVoiceConfig = async (): Promise<VoiceConfig> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.get(ADMIN_AGENT_ENDPOINTS.VOICE_CONFIG, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export const updateVoiceConfig = async (
  voiceConfig: VoiceConfig
): Promise<any> => {
  try {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      throw new Error("Not authenticated as admin");
    }

    const response = await api.post(
      ADMIN_AGENT_ENDPOINTS.VOICE_CONFIG,
      voiceConfig,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  } catch (error: any) {
    throw new Error(getErrorMessage(error));
  }
};

export default api;
