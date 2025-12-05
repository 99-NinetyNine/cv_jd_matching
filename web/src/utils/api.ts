/**
 * API utility functions for authenticated requests
 * Centralizes token management and axios configuration
 */

import axios from 'axios';
import type { AxiosInstance, AxiosRequestConfig } from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Get authorization headers with JWT token from localStorage
 * Reusable function to avoid code duplication
 */
export const getAuthHeaders = (): Record<string, string> => {
    const token = localStorage.getItem('token');
    return token ? { Authorization: `Bearer ${token}` } : {};
};

/**
 * Create axios config with auth headers merged in
 */
export const withAuth = (config: AxiosRequestConfig = {}): AxiosRequestConfig => {
    return {
        ...config,
        headers: {
            ...config.headers,
            ...getAuthHeaders(),
        },
    };
};

/**
 * Configured axios instance with automatic auth headers
 * Use this for all authenticated API calls
 */
export const api: AxiosInstance = axios.create({
    baseURL: API_URL,
});

// Add request interceptor to automatically include auth headers
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Add response interceptor to handle 401 errors globally
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Token expired or invalid - clear auth and redirect to login
            localStorage.removeItem('token');
            localStorage.removeItem('role');
            localStorage.removeItem('isPremium');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

/**
 * Export API_URL for components that need it (WebSocket, etc.)
 */
export { API_URL };

/**
 * Legacy export for backward compatibility
 * @deprecated Use `api` instance instead
 */
export const apiClient = api;
