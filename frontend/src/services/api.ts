import axios from 'axios';

const API_URL = 'http://localhost:8001/api';

const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

// Add a request interceptor to add the auth token to requests
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor to handle 401 Unauthorized responses
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access (e.g., redirect to login)
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export interface Strategy {
  id: number;
  name: string;
  description: string;
  script: string;
  created_at: string;
  updated_at: string;
  owner_id: number;
  is_public: boolean;
  // Add other fields as defined in your backend schema schemas.Strategy
}

export const getStrategies = async (): Promise<Strategy[]> => {
  const response = await apiClient.get<Strategy[]>('/strategies/');
  return response.data;
};

export interface CreateStrategyData {
  name: string;
  description: string;
  is_public: boolean;
  script?: string;
}

export const createStrategy = async (data: CreateStrategyData): Promise<Strategy> => {
  const response = await apiClient.post<Strategy>('/strategies/', data);
  return response.data;
};

// Add other API functions here as needed, e.g., for portfolio, trading, etc.

export default apiClient;
