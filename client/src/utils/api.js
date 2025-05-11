/**
 * API configuration
 */

// Base API URL - will fallback to the proxy setting in development
// and use the explicit URL in production
const getApiUrl = () => {
  // If in production environment, use the deployed backend URL
  if (process.env.NODE_ENV === 'production') {
    return process.env.REACT_APP_API_URL || 'https://predicate-analyzer-api.onrender.com';
  }
  // In development, rely on the proxy setting in package.json
  return '';
};

export const API_BASE_URL = getApiUrl();

/**
 * Get the full API URL for a specific endpoint
 * @param {string} endpoint - The API endpoint (e.g., "/device/K191907")
 * @returns {string} The full API URL
 */
export const getApiEndpoint = (endpoint) => {
  return `${API_BASE_URL}/api${endpoint}`;
};

export default {
  API_BASE_URL,
  getApiEndpoint,
}; 