import axios from 'axios';
import { getApiEndpoint } from '../utils/api';

// Create an axios instance
const api = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Check if a device exists in MongoDB
 * @param {string} kNumber - The K-number to check
 * @returns {Promise<Object>} - Response with exists flag
 */
export const checkDeviceExists = async (kNumber) => {
  try {
    const response = await api.get(getApiEndpoint(`/device/check/${kNumber}`));
    return response.data;
  } catch (error) {
    console.error('Error checking device existence:', error);
    throw error;
  }
};

/**
 * Fetch device data from the API
 * @param {string} kNumber - The K-number to fetch
 * @returns {Promise<Object>} - Device data with predicate relationships
 */
export const fetchDevice = async (kNumber) => {
  try {
    const response = await api.get(getApiEndpoint(`/device/${kNumber}`));
    return response.data;
  } catch (error) {
    console.error('Error fetching device:', error);
    throw error;
  }
};

/**
 * Save device data to MongoDB
 * @param {Object} device - The device data to save
 * @returns {Promise<Object>} - Saved device data
 */
export const saveDevice = async (device) => {
  try {
    const response = await api.post(getApiEndpoint('/device'), device);
    return response.data;
  } catch (error) {
    console.error('Error saving device:', error);
    throw error;
  }
};

export default api; 