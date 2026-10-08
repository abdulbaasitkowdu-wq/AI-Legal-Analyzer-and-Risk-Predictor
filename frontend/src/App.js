// frontend/src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext.jsx';
import { UserProvider, useUser } from './context/UserContext.jsx';
import LegalChatAssistant from './components/assistant/LegalChatAssistant.jsx';
import AdminOverview from './components/AdminOverview.jsx';
import Uploader from './components/Uploader.jsx';
import CalendarSync from './components/CalendarSync.jsx';
import UserProfile from './components/UserProfile.jsx';
import PlatformAnalytics from './components/PlatformAnalytics.jsx';
import PlatformSettings from './components/PlatformSettings.jsx';

import Layout from './components/Layout.jsx';
import Dashboard from './components/Dashboard.jsx';
import UserManagement from './components/UserManagement.jsx';
import Auth from './components/Auth.jsx';

// You can eventually delete this Placeholder function if you aren't using it anymore!
const Placeholder = ({ title }) => (
  <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-100 h-full flex items-center justify-center">
    <h2 className="text-2xl text-gray-400 font-medium">{title} Page Coming Soon</h2>
  </div>
);

function RequireAuth({ children }) {
  const { user } = useUser();
  if (!user?.currentUser) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Auth />} />

      <Route
        path="/*"
        element={
          <RequireAuth>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/upload" element={<Uploader />} />
                <Route path="/calendar" element={<CalendarSync />} />
                <Route path="/assistant" element={<LegalChatAssistant />} />
                <Route path="/profile" element={<UserProfile />} />

                <Route path="/admin" element={<AdminOverview />} />
                <Route path="/admin/users" element={<UserManagement />} />
                <Route path="/admin/analytics" element={<PlatformAnalytics />} />
                <Route path="/admin/settings" element={<PlatformSettings />} />

                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Layout>
          </RequireAuth>
        }
      />
    </Routes>
  );
}

function App() {
  return (
    <ThemeProvider>
      <UserProvider>
        <Router>
          <AppRoutes />
        </Router>
      </UserProvider>
    </ThemeProvider>
  );
}

export default App;