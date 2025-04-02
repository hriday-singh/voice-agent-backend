import React, { useState } from "react";
import { fetchOTPList, deleteOTP, OTP } from "../../services/api";
import "./Admin.css";

const OTPManagement: React.FC = () => {
  const [otpRequests, setOtpRequests] = useState<OTP[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);

  const loadOTPRequests = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchOTPList(currentPage, 10);
      setOtpRequests(result);
      setTotalPages(Math.ceil(result.length / 10));
    } catch (err: any) {
      console.error("Error loading OTPs:", err);
      setError(err.message || "Failed to load OTPs");
      setOtpRequests([]);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteOTP = async (otpId: number) => {
    try {
      await deleteOTP(otpId.toString());
      loadOTPRequests();
    } catch (err: any) {
      setError(err.message || "Failed to delete OTP");
    }
  };

  const handlePageChange = (page: number) => {
    if (page > 0 && page <= totalPages) {
      setCurrentPage(page);
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
          <img
            src="/assets/caw-tech-logo.gif"
            alt="Loading..."
            className="w-16 h-16"
          />
          <p className="mt-4 text-[#6c6c6c]">Loading OTPs...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="bg-white shadow-md rounded-lg p-6">
        <h2 className="text-2xl font-bold text-[#140d0c] mb-6">
          OTP Management
        </h2>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-600 rounded-md text-sm mb-4">
            {error}
          </div>
        )}

        <div className="mb-4 flex justify-end">
          <button
            onClick={() => loadOTPRequests()}
            className="bg-[#ffcc33] text-[#140d0c] px-4 py-1 rounded hover:bg-[#ffcc33]/90"
          >
            Refresh
          </button>
        </div>

        {otpRequests.length > 0 ? (
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
                    Description
                  </th>
                  <th className="px-4 py-2 text-left text-sm font-medium text-[#140d0c]">
                    Created At
                  </th>
                  <th className="px-4 py-2 text-left text-sm font-medium text-[#140d0c]">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-[#e7e2d3]">
                {otpRequests.map((request) => (
                  <tr key={request.id} className="hover:bg-[#f2efe3]/50">
                    <td className="px-4 py-3 text-sm font-mono">
                      {request.code}
                    </td>
                    <td className="px-4 py-3 text-sm">{request.max_uses}</td>
                    <td className="px-4 py-3 text-sm">
                      {request.remaining_uses}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {request.description || "-"}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {formatDate(request.created_at)}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {request.remaining_uses > 0 && (
                        <div className="flex space-x-2">
                          <button
                            onClick={() => handleDeleteOTP(request.id)}
                            className="bg-red-500 hover:bg-red-600 text-white px-2 py-1 rounded text-xs"
                          >
                            Delete
                          </button>
                        </div>
                      )}
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
          <div className="mt-4 flex justify-center">
            <nav className="flex items-center space-x-2">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="px-3 py-1 rounded border border-[#e7e2d3] disabled:opacity-50"
              >
                Previous
              </button>

              {Array.from({ length: totalPages }, (_, i) => i + 1).map(
                (page) => (
                  <button
                    key={page}
                    onClick={() => handlePageChange(page)}
                    className={`px-3 py-1 rounded ${
                      currentPage === page
                        ? "bg-[#ffcc33] text-[#140d0c] border border-[#ffcc33]"
                        : "border border-[#e7e2d3]"
                    }`}
                  >
                    {page}
                  </button>
                )
              )}

              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="px-3 py-1 rounded border border-[#e7e2d3] disabled:opacity-50"
              >
                Next
              </button>
            </nav>
          </div>
        )}
      </div>
    </div>
  );
};

export default OTPManagement;
