import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';

const ProtectedRoute: React.FC = () => {
  const token = localStorage.getItem('authToken');

  if (!token) {
    // User not authenticated, redirect to login page
    // You can also pass the current location to redirect back after login
    // e.g., <Navigate to="/login" state={{ from: location }} replace />
    return <Navigate to="/login" replace />;
  }

  // User is authenticated, render the child routes
  return <Outlet />;
};

export default ProtectedRoute;
