import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authAPI } from '../lib/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('jshost_token');
    const savedUser = localStorage.getItem('jshost_user');
    if (token && savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch {
        localStorage.removeItem('jshost_token');
        localStorage.removeItem('jshost_user');
      }
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await authAPI.login({ email, password });
    const { token, user: userData } = res.data;
    localStorage.setItem('jshost_token', token);
    localStorage.setItem('jshost_user', JSON.stringify(userData));
    setUser(userData);
    return userData;
  }, []);

  const register = useCallback(async (email, password) => {
    const res = await authAPI.register({ email, password });
    const { token, user: userData } = res.data;
    localStorage.setItem('jshost_token', token);
    localStorage.setItem('jshost_user', JSON.stringify(userData));
    setUser(userData);
    return userData;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('jshost_token');
    localStorage.removeItem('jshost_user');
    setUser(null);
  }, []);

  const hasPermission = useCallback((key) => {
    if (!user || !user.permissions) return false;
    return user.permissions.includes(key);
  }, [user]);

  const refreshUser = useCallback(async () => {
    try {
      const res = await authAPI.me();
      const userData = res.data.user;
      localStorage.setItem('jshost_user', JSON.stringify(userData));
      setUser(userData);
    } catch {}
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, hasPermission, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
