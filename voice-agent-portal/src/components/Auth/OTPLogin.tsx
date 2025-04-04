import React, { useState } from "react";
import { Link } from "react-router-dom";
import { loginWithOTP } from "../../services/auth";
import AnimatedLogo from "../Common/AnimatedLogo";
import "./Auth.css";

interface OTPLoginProps {
  onLoginSuccess: () => void;
}

const OTPLogin: React.FC<OTPLoginProps> = ({ onLoginSuccess }) => {
  const [otpCode, setOtpCode] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!otpCode.trim()) {
      setError("Please enter an OTP code");
      return;
    }

    setLoading(true);
    setError(null);

    const result = await loginWithOTP(otpCode);

    setLoading(false);

    if (result.success) {
      onLoginSuccess();
    } else {
      setError(
        "Invalid OTP or credits exhausted. Please contact hello@caw.tech"
      );
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#140d0c] py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full bg-[#f2efe3] rounded-lg shadow-xl p-8">
        <div className="flex flex-col items-center mb-8">
          <AnimatedLogo
            gifSrc="/assets/caw-tech-logo.gif"
            fallbackSrc="/assets/caw-tech-logo.svg"
            alt="CAW Tech Logo"
            height={80}
            className="mb-4"
          />
          <h2 className="text-2xl font-bold text-[#140d0c]">
            Voice Agent Portal
          </h2>
          <p className="text-sm text-[#6c6c6c] mt-1">
            Enter your one-time password to access the portal
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label
              htmlFor="otp"
              className="block text-sm font-medium text-[#140d0c]"
            >
              One-Time Password
            </label>
            <input
              type="text"
              id="otp"
              value={otpCode}
              onChange={(e) => setOtpCode(e.target.value)}
              placeholder="Enter your OTP code"
              disabled={loading}
              className="mt-1 block w-full px-3 py-2 bg-white border border-[#e7e2d3] rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#ffcc33] focus:border-transparent"
            />
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-600 rounded-md text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-[#140d0c] bg-[#ffcc33] hover:bg-[#ffcc33]/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#ffcc33] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Logging in..." : "Login"}
          </button>
        </form>

        <div className="mt-6 text-center">
          <Link
            to="/admin/login"
            className="text-sm text-[#140d0c] hover:text-[#ffcc33] font-medium"
          >
            Admin? Login here
          </Link>
          <div className="mt-2">
            <p className="text-sm text-[#140d0c]">
              Need an OTP? Contact us using{" "}
              <a
                href="mailto:hello@caw.tech"
                className="text-[#140d0c] hover:text-[#ffcc33] font-medium"
              >
                hello@caw.tech
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OTPLogin;
