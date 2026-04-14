import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../../../stores/authStore';
import { AlertCircle, Check, Lock, Shield } from 'lucide-react';
import TwoFactorSetup from '../../auth/pages/TwoFactorSetup';
import api from '../../../services/api';

export const SecuritySettingsPage: React.FC = () => {
  const { user } = useAuthStore();
  const [twoFAEnabled, setTwoFAEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showTwoFASetup, setShowTwoFASetup] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // Fetch current 2FA status
  useEffect(() => {
    const fetchTwoFAStatus = async () => {
      try {
        const response = await api.get('/auth/me');
        // Check if user has totp_enabled flag from backend
        // For now, we'll show this from user profile
        setTwoFAEnabled(response.data.totp_enabled || false);
        setLoading(false);
      } catch (err) {
        console.error('Failed to fetch 2FA status:', err);
        setLoading(false);
      }
    };

    fetchTwoFAStatus();
  }, []);

  const handleDisable2FA = async () => {
    if (!window.confirm('Are you sure? You will need to re-enable 2FA later.')) {
      return;
    }

    try {
      setLoading(true);
      // Call backend to disable 2FA (requires password verification in the backend)
      await api.post('/auth/2fa/disable', {
        password: window.prompt('Enter your password to disable 2FA:'),
      });
      setTwoFAEnabled(false);
      setSuccessMessage('2FA has been disabled successfully.');
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to disable 2FA');
      setTimeout(() => setErrorMessage(''), 3000);
    } finally {
      setLoading(false);
    }
  };

  const handleSetupComplete = () => {
    // After successful 2FA setup, update status
    setTwoFAEnabled(true);
    setShowTwoFASetup(false);
    setSuccessMessage('2FA has been enabled successfully.');
    setTimeout(() => setSuccessMessage(''), 3000);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin">
          <Shield className="w-6 h-6" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <div className="space-y-6">
        {/* Page Header */}
        <div className="border-b pb-6">
          <h1 className="text-2xl font-bold text-gray-900">Security Settings</h1>
          <p className="text-gray-600 mt-2">Manage your account security and authentication</p>
        </div>

        {/* Success/Error Messages */}
        {successMessage && (
          <div className="flex items-center gap-3 p-4 rounded-lg bg-green-50 border border-green-200">
            <Check className="w-5 h-5 text-green-600" />
            <span className="text-green-700">{successMessage}</span>
          </div>
        )}

        {errorMessage && (
          <div className="flex items-center gap-3 p-4 rounded-lg bg-red-50 border border-red-200">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <span className="text-red-700">{errorMessage}</span>
          </div>
        )}

        {/* Two-Factor Authentication Section */}
        <div className="rounded-lg border border-gray-200 p-6 bg-white">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Lock className="w-5 h-5 text-blue-600" />
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Two-Factor Authentication (2FA)
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Add an extra layer of security to your account
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div
                className={`inline-flex px-3 py-1 rounded-full text-sm font-medium ${
                  twoFAEnabled
                    ? 'bg-green-100 text-green-800'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                {twoFAEnabled ? '✓ Enabled' : 'Disabled'}
              </div>
            </div>
          </div>

          <div className="space-y-4">
            {/* 2FA Status Info */}
            <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
              <p className="text-sm text-blue-900">
                <strong>What is 2FA?</strong> Two-factor authentication requires you to provide two different types of information to log in - your password and a code from an authenticator app or backup code. This significantly improves your account security.
              </p>
            </div>

            {/* Current Status Info */}
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-900">
                Current Status: <span className={twoFAEnabled ? 'text-green-600' : 'text-gray-600'}>
                  {twoFAEnabled ? 'Enabled' : 'Not Enabled'}
                </span>
              </p>
              {twoFAEnabled ? (
                <p className="text-sm text-gray-600">
                  Your account is protected with 2FA. You can disable it below if needed.
                </p>
              ) : (
                <p className="text-sm text-gray-600">
                  Enable 2FA to secure your account with an authenticator app.
                </p>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3 pt-2">
              {!twoFAEnabled ? (
                <button
                  onClick={() => setShowTwoFASetup(true)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm transition"
                >
                  Enable 2FA
                </button>
              ) : (
                <button
                  onClick={handleDisable2FA}
                  disabled={loading}
                  className="px-4 py-2 bg-red-50 text-red-600 border border-red-200 rounded-lg hover:bg-red-100 font-medium text-sm transition disabled:opacity-50"
                >
                  {loading ? 'Disabling...' : 'Disable 2FA'}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Other Security Settings */}
        <div className="rounded-lg border border-gray-200 p-6 bg-white">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Password & Session Management</h3>
          <div className="space-y-3">
            <button className="w-full text-left px-4 py-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition text-gray-900 font-medium">
              Change Password
            </button>
            <button className="w-full text-left px-4 py-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition text-gray-900 font-medium">
              View Active Sessions
            </button>
            <button className="w-full text-left px-4 py-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition text-gray-900 font-medium">
              Login Activity
            </button>
          </div>
        </div>

        {/* 2FA Setup Modal */}
        {showTwoFASetup && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-2xl w-full max-h-96 overflow-auto">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold">Enable Two-Factor Authentication</h3>
                  <button
                    onClick={() => setShowTwoFASetup(false)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    ✕
                  </button>
                </div>
                <TwoFactorSetup
                  onComplete={handleSetupComplete}
                  onCancel={() => setShowTwoFASetup(false)}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SecuritySettingsPage;
