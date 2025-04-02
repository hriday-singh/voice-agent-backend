import React, { useState } from "react";
import { changeAdminPassword } from "../../services/api";
import "./Admin.css";

const PasswordChange: React.FC = () => {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Password validation
  const validatePassword = (password: string): boolean => {
    // Check minimum length
    if (password.length < 8) return false;

    // Check for at least one uppercase letter
    if (!/[A-Z]/.test(password)) return false;

    // Check for at least one lowercase letter
    if (!/[a-z]/.test(password)) return false;

    // Check for at least one number
    if (!/[0-9]/.test(password)) return false;

    // Check for at least one special character (more permissive)
    if (!/[^A-Za-z0-9]/.test(password)) return false;

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Reset states
    setError(null);
    setSuccess(null);

    // Validate passwords
    if (!currentPassword || !newPassword || !confirmPassword) {
      setError("All fields are required");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("New password and confirmation must match");
      return;
    }

    if (!validatePassword(newPassword)) {
      setError(
        "New password must be at least 8 characters long and include uppercase, lowercase, number and special character"
      );
      return;
    }

    if (currentPassword === newPassword) {
      setError("New password must be different from current password");
      return;
    }

    setLoading(true);

    try {
      const result = await changeAdminPassword(currentPassword, newPassword);

      if (result.success) {
        setSuccess(result.message || "Password changed successfully");
        // Clear form
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
      } else {
        setError(result.error || "Failed to change password");
      }
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="bg-white shadow-md rounded-lg p-6 max-w-md mx-auto">
        <h2 className="text-2xl font-bold text-[#140d0c] mb-6">
          Change Admin Password
        </h2>

        {success && (
          <div className="p-4 mb-4 bg-green-50 border border-green-200 text-green-700 rounded-md">
            {success}
          </div>
        )}

        {error && (
          <div className="p-4 mb-4 bg-red-50 border border-red-200 text-red-700 rounded-md">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label
              htmlFor="currentPassword"
              className="block text-sm font-medium text-[#140d0c] mb-1"
            >
              Current Password
            </label>
            <input
              type="password"
              id="currentPassword"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#ffcc33] focus:border-transparent"
              disabled={loading}
              required
              autoComplete="current-password"
            />
          </div>

          <div className="mb-4">
            <label
              htmlFor="newPassword"
              className="block text-sm font-medium text-[#140d0c] mb-1"
            >
              New Password
            </label>
            <input
              type="password"
              id="newPassword"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#ffcc33] focus:border-transparent"
              disabled={loading}
              required
              autoComplete="new-password"
            />
            <p className="mt-1 text-xs text-[#6c6c6c]">
              Password must be at least 8 characters long and include uppercase,
              lowercase, number and special character.
            </p>
          </div>

          <div className="mb-6">
            <label
              htmlFor="confirmPassword"
              className="block text-sm font-medium text-[#140d0c] mb-1"
            >
              Confirm New Password
            </label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#ffcc33] focus:border-transparent"
              disabled={loading}
              required
              autoComplete="new-password"
            />
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-[#ffcc33] text-[#140d0c] rounded-md hover:bg-[#ffcc33]/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#ffcc33] disabled:opacity-50"
            >
              {loading ? "Changing Password..." : "Change Password"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default PasswordChange;
