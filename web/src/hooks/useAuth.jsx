import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api, { ApiError } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('aerovital_auth_token'));
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  const fetchCurrentUser = useCallback(async () => {
    const currentToken = localStorage.getItem('aerovital_auth_token');
    if (!currentToken) {
      setUser(null);
      setIsLoading(false);
      return null;
    }

    try {
      setIsLoading(true);
      setAuthError(null);
      const userData = await api.auth.getMe();
      setUser(userData);
      return userData;
    } catch (err) {
      console.warn('Auth validation failed:', err.message);
      if (err instanceof ApiError && err.status === 401) {
        setToken(null);
        setUser(null);
        localStorage.removeItem('aerovital_auth_token');
      } else {
        setAuthError(err.message);
      }
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCurrentUser();

    const handleExpired = () => {
      setToken(null);
      setUser(null);
      setAuthError('Session expired. Please log in again.');
    };

    window.addEventListener('aerovital:auth_expired', handleExpired);
    return () => window.removeEventListener('aerovital:auth_expired', handleExpired);
  }, [fetchCurrentUser]);

  const login = async (username, password) => {
    setIsLoading(true);
    setAuthError(null);
    try {
      const data = await api.auth.login(username, password);
      setToken(data.token);
      setUser({
        user_id: data.user_id,
        username: data.username,
        pilot: data.pilot,
      });
      return data;
    } catch (err) {
      setAuthError(err.message || 'Login failed');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await api.auth.logout();
    } catch (err) {
      console.warn('Logout API error:', err);
    } finally {
      setToken(null);
      setUser(null);
      setIsLoading(false);
    }
  };

  const value = {
    token,
    user,
    pilot: user?.pilot || null,
    isAuthenticated: !!token && !!user,
    isLoading,
    authError,
    login,
    logout,
    refreshUser: fetchCurrentUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default useAuth;
