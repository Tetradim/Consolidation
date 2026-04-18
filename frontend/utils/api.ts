/**
 * Shared axios instance.
 * Attaches X-API-Key to every outgoing request from EXPO_PUBLIC_API_KEY.
 * 401 responses are left to fail naturally — callers surface errors as needed.
 */
import axios from 'axios';
import { getApiKey } from './apiKey';
import { BACKEND_URL } from '../constants/config';

export const api = axios.create({
  baseURL: BACKEND_URL,
  timeout: 15_000,
});

api.interceptors.request.use((config) => {
  const key = getApiKey();
  if (key) {
    config.headers['X-API-Key'] = key;
  }
  return config;
});
