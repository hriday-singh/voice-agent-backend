import React, { useState, useEffect } from "react";
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
  Link,
} from "react-router-dom";
import AdminLogin from "./components/Auth/AdminLogin";
import OTPLogin from "./components/Auth/OTPLogin";
import VoiceAgentPage from "./components/VoiceAgent/VoiceAgentPage";
import OTPManagement from "./components/Admin/OTPManagement";
import OTPList from "./components/Admin/OTPList";
import AgentConfiguration from "./components/Admin/AgentConfiguration";
import PasswordChange from "./components/Admin/PasswordChange";
import AnimatedLogo from "./components/Common/AnimatedLogo";
import { isAuthenticated, logout } from "./services/auth";
import "./App.css";
import { HiMenu, HiX } from "react-icons/hi";

const App: React.FC = () => {
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(isAuthenticated());
  const [userType, setUserType] = useState<string | null>(
    localStorage.getItem("userType")
  );
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Check authentication status when component mounts
  useEffect(() => {
    setIsLoggedIn(isAuthenticated());
    setUserType(localStorage.getItem("userType"));
  }, []);

  const handleLoginSuccess = () => {
    setIsLoggedIn(true);
    setUserType(localStorage.getItem("userType"));
  };

  const handleLogout = () => {
    logout();
    setIsLoggedIn(false);
    setUserType(null);
    setIsMobileMenuOpen(false);
  };

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false);
  };

  // Protected route component
  const ProtectedRoute: React.FC<{
    children: React.ReactNode;
    allowedUserType?: string;
  }> = ({ children, allowedUserType }) => {
    if (!isLoggedIn) {
      return <Navigate to="/login" replace />;
    }

    if (allowedUserType && userType !== allowedUserType) {
      return <Navigate to="/" replace />;
    }

    return <>{children}</>;
  };

  return (
    <Router>
      <div className="app dark">
        {isLoggedIn && (
          <header className="bg-[#0c0807] text-[#f2efe3] border-b border-[#31261a] shadow-md relative">
            <div className="container mx-auto px-4 py-4">
              <div className="flex justify-between items-center">
                <Link
                  to="/"
                  className="text-[#f2efe3] hover:text-[#ffcc33] transition-colors"
                  onClick={closeMobileMenu}
                >
                  <h1 className="text-xl font-semibold flex items-center">
                    <AnimatedLogo
                      gifSrc="/assets/caw-tech-logo.gif"
                      fallbackSrc="/assets/caw-tech-logo.svg"
                      alt="CAW Tech Logo"
                      height={40}
                      className="logo mr-3"
                    />
                    <span style={{ display: "inline-block", color: "#f2efe3" }}>
                      Voice Agent Portal
                    </span>
                  </h1>
                </Link>

                {/* Desktop Navigation */}
                <div className="hidden md:flex items-center space-x-6">
                  {userType === "admin" && (
                    <nav className="flex space-x-6">
                      <Link
                        to="/admin/otps"
                        className="text-[#f2efe3] hover:text-[#ffcc33] transition-colors font-medium relative after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-0 after:bg-[#ffcc33] after:transition-all hover:after:w-full"
                      >
                        OTP Management
                      </Link>
                      <Link
                        to="/admin/agents"
                        className="text-[#f2efe3] hover:text-[#ffcc33] transition-colors font-medium relative after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-0 after:bg-[#ffcc33] after:transition-all hover:after:w-full"
                      >
                        Agent Configuration
                      </Link>
                      <Link
                        to="/admin/password"
                        className="text-[#f2efe3] hover:text-[#ffcc33] transition-colors font-medium relative after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-0 after:bg-[#ffcc33] after:transition-all hover:after:w-full"
                      >
                        Change Password
                      </Link>
                    </nav>
                  )}
                  <button
                    className="px-4 py-2 rounded-md bg-transparent border border-[#ffcc33] text-[#ffcc33] hover:bg-[#ffcc33] hover:text-[#0c0807] transition-colors"
                    onClick={handleLogout}
                  >
                    Logout
                  </button>
                </div>

                {/* Mobile Menu Button */}
                <button
                  className="md:hidden text-[#f2efe3] hover:text-[#ffcc33] transition-colors"
                  onClick={toggleMobileMenu}
                >
                  {isMobileMenuOpen ? (
                    <HiX className="h-6 w-6" />
                  ) : (
                    <HiMenu className="h-6 w-6" />
                  )}
                </button>
              </div>

              {/* Mobile Navigation */}
              {isMobileMenuOpen && (
                <div className="md:hidden mt-4 pb-4 border-t border-[#31261a] pt-4">
                  {userType === "admin" && (
                    <nav className="flex flex-col space-y-4">
                      <Link
                        to="/admin/otps"
                        className="text-[#f2efe3] hover:text-[#ffcc33] transition-colors font-medium py-2"
                        onClick={closeMobileMenu}
                      >
                        OTP Management
                      </Link>
                      <Link
                        to="/admin/agents"
                        className="text-[#f2efe3] hover:text-[#ffcc33] transition-colors font-medium py-2"
                        onClick={closeMobileMenu}
                      >
                        Agent Configuration
                      </Link>
                      <Link
                        to="/admin/password"
                        className="text-[#f2efe3] hover:text-[#ffcc33] transition-colors font-medium py-2"
                        onClick={closeMobileMenu}
                      >
                        Change Password
                      </Link>
                    </nav>
                  )}
                  <div className="mt-4">
                    <button
                      className="w-full px-4 py-2 rounded-md bg-transparent border border-[#ffcc33] text-[#ffcc33] hover:bg-[#ffcc33] hover:text-[#0c0807] transition-colors"
                      onClick={handleLogout}
                    >
                      Logout
                    </button>
                  </div>
                </div>
              )}
            </div>
          </header>
        )}

        <main className="flex-1 flex flex-col bg-[#f2efe3]">
          <Routes>
            <Route
              path="/login"
              element={
                isLoggedIn ? (
                  <Navigate to="/" replace />
                ) : (
                  <OTPLogin onLoginSuccess={handleLoginSuccess} />
                )
              }
            />

            <Route
              path="/admin/login"
              element={
                isLoggedIn ? (
                  <Navigate to="/admin/otps" replace />
                ) : (
                  <AdminLogin onLoginSuccess={handleLoginSuccess} />
                )
              }
            />

            <Route
              path="/admin/*"
              element={
                <ProtectedRoute allowedUserType="admin">
                  <div className="min-h-screen bg-[#f2efe3]">
                    <Routes>
                      <Route path="otps" element={<OTPList />} />
                      <Route path="otp-requests" element={<OTPManagement />} />
                      <Route path="agents" element={<AgentConfiguration />} />
                      <Route path="password" element={<PasswordChange />} />
                      <Route
                        index
                        element={<Navigate to="/admin/otps" replace />}
                      />
                    </Routes>
                  </div>
                </ProtectedRoute>
              }
            />

            <Route
              path="/"
              element={
                isLoggedIn ? (
                  <VoiceAgentPage />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />

            <Route
              path="/agent/:agentId"
              element={
                isLoggedIn ? (
                  <VoiceAgentPage />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

export default App;
