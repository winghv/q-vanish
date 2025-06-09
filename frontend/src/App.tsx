import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute'; 
import Dashboard from './pages/Dashboard';
import Strategies from './pages/Strategies';
import Backtest from './pages/Backtest';
import Trading from './pages/Trading';
import Portfolio from './pages/Portfolio';
import AIAssistant from './pages/AIAssistant';
import Settings from './pages/Settings';
import NotFound from './pages/NotFound';
import LoginPage from './pages/LoginPage'; 

function App() {
  // Simple notification function
  const showNotification = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    console.log(`[${type.toUpperCase()}] ${message}`);
    alert(`[${type.toUpperCase()}] ${message}`);
  };

  // Make showNotification available globally for other components
  (window as any).showNotification = showNotification;

  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} /> 
        <Route path="/" element={<ProtectedRoute />}> 
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="strategies" element={<Strategies />} />
            <Route path="backtest" element={<Backtest />} />
            <Route path="trading" element={<Trading />} />
            <Route path="portfolio" element={<Portfolio />} />
            <Route path="ai-assistant" element={<AIAssistant />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFound />} /> 
      </Routes>
    </>
  );
}

export default App;