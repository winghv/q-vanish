import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

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

// Trading/Portfolio
export interface Position {
  symbol: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  value: number;
  profit_loss: number;
  profit_loss_percent: number;
}

export const getPositions = async (): Promise<Position[]> => {
  const res = await apiClient.get<Position[]>('/portfolio/positions');
  return res.data;
};

export interface TradeOrder {
  id: string;
  symbol: string;
  type: 'buy' | 'sell';
  status: 'pending' | 'filled' | 'canceled';
  quantity: number;
  price: number;
  total: number;
  timestamp: string;
}

export const getOrders = async (): Promise<TradeOrder[]> => {
  const res = await apiClient.get<TradeOrder[]>('/orders');
  return res.data;
};

export interface PlaceOrderData {
  symbol: string;
  type: 'buy' | 'sell';
  quantity: number;
  price?: number;
  order_type: 'market' | 'limit';
}

export const placeOrder = async (data: PlaceOrderData): Promise<TradeOrder> => {
  const res = await apiClient.post<TradeOrder>('/orders', data);
  return res.data;
};

// Portfolio
export interface Asset {
  symbol: string;
  name: string;
  shares: number;
  price: number;
  value: number;
  allocation: number;
  day_change: number;
  total_return: number;
}

export const getAssets = async (): Promise<Asset[]> => {
  const res = await apiClient.get<Asset[]>('/portfolio/assets');
  return res.data;
};

export interface Performance {
  balance: number;
  day_change: number;
  week_change: number;
  month_change: number;
  year_change: number;
  total_return: number;
  history: { date: string; value: number }[];
}

export const getPerformance = async (): Promise<Performance> => {
  const res = await apiClient.get<Performance>('/portfolio/performance');
  return res.data;
};

// Backtest
export interface BacktestParams {
  strategy: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  symbol: string;
}

export interface BacktestResult {
  total_return: number;
  annual_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  trades: number;
  equity: { date: string; value: number }[];
}

export const runBacktest = async (params: BacktestParams): Promise<BacktestResult> => {
  const res = await apiClient.post<BacktestResult>('/backtest', params);
  return res.data;
};

// Dashboard
export const getDashboardPerformance = async (): Promise<{ date: string; value: number }[]> => {
  const res = await apiClient.get<{ date: string; value: number }[]>('/dashboard/performance');
  return res.data;
};
export const getActiveStrategies = async (): Promise<any[]> => {
  const res = await apiClient.get<any[]>('/dashboard/active_strategies');
  return res.data;
};
export const getRecentTrades = async (): Promise<any[]> => {
  const res = await apiClient.get<any[]>('/dashboard/recent_trades');
  return res.data;
};
export const getNotifications = async (): Promise<any[]> => {
  const res = await apiClient.get<any[]>('/dashboard/notifications');
  return res.data;
};

// Settings/User
export interface UserProfile {
  name: string;
  email: string;
  avatar: string;
}
export const getUserProfile = async (): Promise<UserProfile> => {
  const res = await apiClient.get<UserProfile>('/user/profile');
  return res.data;
};
export const updateUserProfile = async (data: UserProfile): Promise<UserProfile> => {
  const res = await apiClient.put<UserProfile>('/user/profile', data);
  return res.data;
};
export interface NotificationSettings {
  email_alerts: boolean;
  trading_alerts: boolean;
  market_updates: boolean;
  weekly_reports: boolean;
}
export const getNotificationSettings = async (): Promise<NotificationSettings> => {
  const res = await apiClient.get<NotificationSettings>('/user/notifications');
  return res.data;
};
export const updateNotificationSettings = async (data: NotificationSettings): Promise<NotificationSettings> => {
  const res = await apiClient.put<NotificationSettings>('/user/notifications', data);
  return res.data;
};
export interface ApiKey {
  provider: string;
  key: string;
  status: 'active' | 'inactive';
  last_used: string;
}
export const getApiKeys = async (): Promise<ApiKey[]> => {
  const res = await apiClient.get<ApiKey[]>('/user/api_keys');
  return res.data;
};
export const addApiKey = async (data: { provider: string; key: string }): Promise<ApiKey> => {
  const res = await apiClient.post<ApiKey>('/user/api_keys', data);
  return res.data;
};
export const deleteApiKey = async (provider: string): Promise<void> => {
  await apiClient.delete(`/user/api_keys/${provider}`);
};

// AI Assistant
export const sendAIMessage = async (message: string): Promise<string> => {
  const res = await apiClient.post<{ reply: string }>('/ai/assistant', { message });
  return res.data.reply;
};

// Auth
export const login = async (username: string, password: string): Promise<{ access_token: string }> => {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);
  const res = await apiClient.post<{ access_token: string }>('/auth/token', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return res.data;
};

export default apiClient;
