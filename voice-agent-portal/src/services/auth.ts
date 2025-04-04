import api from "./api";

// Utility function to extract error message from error response
const getErrorMessage = (error: any): string => {
  console.error("Error response:", error.response?.data);

  if (error.response?.data) {
    const data = error.response.data;

    // If data is a validation error array
    if (Array.isArray(data)) {
      const messages = data.map((err: any) => {
        if (err.msg) return err.msg;
        if (err.message) return err.message;
        return String(err);
      });
      return messages.join(", ");
    }

    // If data is an object with validation errors
    if (data.detail && Array.isArray(data.detail)) {
      const messages = data.detail.map((err: any) => {
        if (err.msg) return err.msg;
        if (err.message) return err.message;
        return String(err);
      });
      return messages.join(", ");
    }

    // If data has a simple detail message
    if (data.detail && typeof data.detail === "string") {
      return data.detail;
    }

    // If data has a simple message
    if (data.message && typeof data.message === "string") {
      return data.message;
    }

    // If data is a simple string
    if (typeof data === "string") {
      return data;
    }

    // If we have a validation error object
    if (data.type === "validation_error") {
      return String(data.msg || "Validation error");
    }
  }

  return error.message || "An error occurred";
};

// Admin login
export const loginAdmin = async (username: string, password: string) => {
  try {
    const formData = new URLSearchParams();
    formData.append("username", username.trim());
    formData.append("password", password.trim());

    const response = await api.post("/auth/login/admin", formData, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });

    // Save tokens and user type
    localStorage.setItem("token", response.data.access_token);
    localStorage.setItem("adminToken", response.data.access_token);
    localStorage.setItem("userType", "admin");

    return {
      success: true,
    };
  } catch (error: any) {
    console.error("Login error:", error);
    return {
      success: false,
      error: getErrorMessage(error),
    };
  }
};

// OTP login
export const loginWithOTP = async (otpCode: string) => {
  try {
    const response = await api.post("/otps/login", {
      otp_code: otpCode,
    });

    const { access_token } = response.data;
    localStorage.setItem("token", access_token);
    localStorage.setItem("userType", "otp");

    return { success: true };
  } catch (error: any) {
    return {
      success: false,
      error: getErrorMessage(error),
    };
  }
};

// Check if user is logged in
export const isAuthenticated = (): boolean => {
  return !!localStorage.getItem("token");
};

// Logout
export const logout = (): void => {
  localStorage.removeItem("token");
  localStorage.removeItem("userType");
};
