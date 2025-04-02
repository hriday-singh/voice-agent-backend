import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  requestOTP,
  OTPRequestForm as OTPRequestFormData,
} from "../../services/api";
import AnimatedLogo from "../Common/AnimatedLogo";

interface OTPRequestFormProps {
  onRequestSuccess?: () => void;
}

const OTPRequestForm: React.FC<OTPRequestFormProps> = ({
  onRequestSuccess,
}) => {
  const [formData, setFormData] = useState<OTPRequestFormData>({
    name: "",
    email: "",
    phoneNumber: "",
    purpose: "",
    company: "",
  });
  const [status, setStatus] = useState<{
    requestId: string;
    message: string;
    status: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const result = await requestOTP(formData);
      setStatus({
        requestId: result.request_id,
        message: result.message,
        status: result.status,
      });
      if (onRequestSuccess) {
        onRequestSuccess();
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
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
            Request Voice Agent Access
          </h2>
          <p className="text-sm text-[#6c6c6c] mt-1">
            Fill out this form to request access to our voice agents
          </p>
        </div>

        {status && (
          <div className="p-4 bg-green-50 border border-green-200 text-green-800 rounded-md mb-6">
            <p className="font-medium">{status.message}</p>
            <p className="text-sm mt-1">Your request is being reviewed.</p>
            <p className="text-sm mt-3">
              Once approved, you'll receive an OTP to access the voice agents.
            </p>
          </div>
        )}

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-600 rounded-md text-sm mb-4">
            {error}
          </div>
        )}

        {!status && (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="name"
                className="block text-sm font-medium text-[#140d0c]"
              >
                Full Name*
              </label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
                minLength={2}
                maxLength={50}
                disabled={loading}
                className="mt-1 block w-full px-3 py-2 bg-white border border-[#e7e2d3] rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#ffcc33] focus:border-transparent"
              />
            </div>

            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-[#140d0c]"
              >
                Email Address*
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                disabled={loading}
                className="mt-1 block w-full px-3 py-2 bg-white border border-[#e7e2d3] rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#ffcc33] focus:border-transparent"
              />
            </div>

            <div>
              <label
                htmlFor="phoneNumber"
                className="block text-sm font-medium text-[#140d0c]"
              >
                Phone Number*
              </label>
              <input
                type="tel"
                id="phoneNumber"
                name="phoneNumber"
                value={formData.phoneNumber}
                onChange={handleChange}
                required
                pattern="^\+?[0-9]{10,15}$"
                placeholder="+919876543210"
                disabled={loading}
                className="mt-1 block w-full px-3 py-2 bg-white border border-[#e7e2d3] rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#ffcc33] focus:border-transparent"
              />
              <p className="text-xs text-[#6c6c6c] mt-1">
                Format: +[country code][number], e.g., +919876543210
              </p>
            </div>

            <div>
              <label
                htmlFor="purpose"
                className="block text-sm font-medium text-[#140d0c]"
              >
                Purpose of Request*
              </label>
              <textarea
                id="purpose"
                name="purpose"
                value={formData.purpose}
                onChange={handleChange}
                required
                minLength={5}
                maxLength={200}
                rows={3}
                disabled={loading}
                className="mt-1 block w-full px-3 py-2 bg-white border border-[#e7e2d3] rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#ffcc33] focus:border-transparent"
              ></textarea>
            </div>

            <div>
              <label
                htmlFor="company"
                className="block text-sm font-medium text-[#140d0c]"
              >
                Company (Optional)
              </label>
              <input
                type="text"
                id="company"
                name="company"
                value={formData.company}
                onChange={handleChange}
                maxLength={100}
                disabled={loading}
                className="mt-1 block w-full px-3 py-2 bg-white border border-[#e7e2d3] rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#ffcc33] focus:border-transparent"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-[#140d0c] bg-[#ffcc33] hover:bg-[#ffcc33]/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#ffcc33] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Submitting..." : "Submit Request"}
            </button>
          </form>
        )}

        <div className="mt-6 text-center">
          <p className="text-sm text-[#6c6c6c]">
            Already have an OTP?{" "}
            <Link
              to="/login"
              className="text-[#140d0c] hover:text-[#ffcc33] font-medium"
            >
              Login here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default OTPRequestForm;
