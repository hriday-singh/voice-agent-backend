import React, { useState, useEffect } from "react";
import {
  fetchOTPList,
  generateOTPs,
  updateOTP,
  deleteOTP,
  OTP,
} from "../../services/api";

const OTPList: React.FC = () => {
  const [otps, setOtps] = useState<OTP[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [showGenerateModal, setShowGenerateModal] = useState<boolean>(false);
  const [showUpdateModal, setShowUpdateModal] = useState<boolean>(false);
  const [selectedOtpId, setSelectedOtpId] = useState<string | null>(null);
  const [newMaxUses, setNewMaxUses] = useState<number>(5);
  const [generateCount, setGenerateCount] = useState<number>(1);
  const [generateMaxUses, setGenerateMaxUses] = useState<number>(5);

  const loadOTPs = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchOTPList(currentPage, 10);
      setOtps(result);
      setTotalPages(Math.ceil(result.length / 10));
    } catch (err: any) {
      console.error("Error loading OTPs:", err);
      setError(err.message || "Failed to load OTPs");
      setOtps([]);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  }, [currentPage]);

  useEffect(() => {
    loadOTPs();
  }, [loadOTPs]);

  const handlePageChange = (page: number) => {
    if (page > 0 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  const handleGenerateOTPs = async () => {
    try {
      const result = await generateOTPs(generateCount, generateMaxUses);
      if (result.success) {
        setShowGenerateModal(false);
        loadOTPs();
      } else {
        setError(result.error || "Failed to generate OTPs");
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleUpdateOTP = async () => {
    if (!selectedOtpId) return;

    try {
      const result = await updateOTP(selectedOtpId, newMaxUses);
      if (result.success) {
        setShowUpdateModal(false);
        loadOTPs();
      } else {
        setError(result.error || "Failed to update OTP");
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDeleteOTP = async (otpId: string) => {
    if (!window.confirm("Are you sure you want to delete this OTP?")) return;

    try {
      const result = await deleteOTP(otpId);
      if (result.success) {
        loadOTPs();
      } else {
        setError(result.error || "Failed to delete OTP");
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center">
          <div className="w-16 h-16 border-4 border-[#ffcc33] border-t-transparent rounded-full animate-spin"></div>
          <p className="mt-4 text-[#6c6c6c]">Loading OTPs...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="bg-white shadow-md rounded-lg p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-[#140d0c]">OTP Management</h2>
          <button
            onClick={() => setShowGenerateModal(true)}
            className="bg-[#ffcc33] text-[#140d0c] px-4 py-2 rounded hover:bg-[#ffcc33]/90"
          >
            Generate OTPs
          </button>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-600 rounded-md text-sm mb-4">
            {error}
          </div>
        )}

        {otps.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-[#e7e2d3]">
              <thead>
                <tr className="bg-[#f2efe3]">
                  <th className="px-4 py-2 text-left text-sm font-medium text-[#140d0c]">
                    Code
                  </th>
                  <th className="px-4 py-2 text-left text-sm font-medium text-[#140d0c]">
                    Max Uses
                  </th>
                  <th className="px-4 py-2 text-left text-sm font-medium text-[#140d0c]">
                    Remaining Uses
                  </th>
                  <th className="px-4 py-2 text-left text-sm font-medium text-[#140d0c]">
                    Created At
                  </th>
                  <th className="px-4 py-2 text-left text-sm font-medium text-[#140d0c]">
                    Status
                  </th>
                  <th className="px-4 py-2 text-left text-sm font-medium text-[#140d0c]">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-[#e7e2d3]">
                {otps.map((otp) => (
                  <tr key={otp.id} className="hover:bg-[#f2efe3]/50">
                    <td className="px-4 py-3 text-sm font-mono">{otp.code}</td>
                    <td className="px-4 py-3 text-sm">{otp.max_uses}</td>
                    <td className="px-4 py-3 text-sm">{otp.remaining_uses}</td>
                    <td className="px-4 py-3 text-sm">
                      {formatDate(otp.created_at)}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span
                        className={`inline-block px-2 py-1 rounded-full text-xs ${
                          otp.remaining_uses > 0
                            ? "bg-green-100 text-green-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {otp.remaining_uses > 0 ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => {
                            setSelectedOtpId(String(otp.id));
                            setNewMaxUses(otp.max_uses);
                            setShowUpdateModal(true);
                          }}
                          className="bg-blue-500 hover:bg-blue-600 text-white px-2 py-1 rounded text-xs"
                        >
                          Update
                        </button>
                        <button
                          onClick={() => handleDeleteOTP(String(otp.id))}
                          className="bg-red-500 hover:bg-red-600 text-white px-2 py-1 rounded text-xs"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">No OTPs found</div>
        )}

        {totalPages > 1 && (
          <div className="mt-4 flex justify-center space-x-2">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="px-3 py-1 rounded bg-[#f2efe3] disabled:opacity-50"
            >
              Previous
            </button>
            <span className="px-3 py-1">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="px-3 py-1 rounded bg-[#f2efe3] disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </div>

      {/* Generate OTPs Modal */}
      {showGenerateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg w-96">
            <h3 className="text-lg font-bold mb-4">Generate OTPs</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Number of OTPs
                </label>
                <input
                  type="number"
                  min="1"
                  value={generateCount}
                  onChange={(e) =>
                    setGenerateCount(Math.max(1, Number(e.target.value)))
                  }
                  className="w-full px-3 py-2 border rounded"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  Maximum Uses per OTP (default: 5)
                </label>
                <input
                  type="number"
                  min="1"
                  value={generateMaxUses}
                  onChange={(e) =>
                    setGenerateMaxUses(Math.max(1, Number(e.target.value)))
                  }
                  className="w-full px-3 py-2 border rounded"
                />
              </div>
              <div className="flex justify-end space-x-2">
                <button
                  onClick={() => setShowGenerateModal(false)}
                  className="px-4 py-2 border rounded hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleGenerateOTPs}
                  className="px-4 py-2 bg-[#ffcc33] text-[#140d0c] rounded hover:bg-[#ffcc33]/90"
                >
                  Generate
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Update OTP Modal */}
      {showUpdateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg w-96">
            <h3 className="text-lg font-bold mb-4">Update OTP</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Maximum Uses
                </label>
                <input
                  type="number"
                  min="1"
                  value={newMaxUses}
                  onChange={(e) =>
                    setNewMaxUses(Math.max(1, Number(e.target.value)))
                  }
                  className="w-full px-3 py-2 border rounded"
                />
              </div>
              <div className="flex justify-end space-x-2">
                <button
                  onClick={() => setShowUpdateModal(false)}
                  className="px-4 py-2 border rounded hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpdateOTP}
                  className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  Update
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OTPList;
