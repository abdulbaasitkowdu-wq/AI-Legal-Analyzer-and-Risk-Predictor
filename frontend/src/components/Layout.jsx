import React from 'react';
import { Shield, LayoutDashboard, UploadCloud, Calendar, User as UserIcon, LogOut, Users, BarChart2, Settings, MessageSquare, Moon, Sun } from 'lucide-react';
import { useLocation, Link, useNavigate, Navigate } from 'react-router-dom';
import { useUser } from '../context/UserContext.jsx';
import { useTheme } from '../context/ThemeContext.jsx';

const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

const Layout = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, setUser } = useUser();
  const { currentUser } = user;
  const { darkMode, toggleDarkMode } = useTheme();

  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }

  // Only real admin roles from login — do not use .includes('Admin') or phrases like
  // "System Admin / Tester" would incorrectly open the admin portal.
  const isAdmin =
    currentUser.role === 'Admin' ||
    currentUser.role === 'Super Admin';

  // Navigation for Normal Users
  const userNavItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Upload Document', path: '/upload', icon: UploadCloud },
    { name: 'Calendar Sync', path: '/calendar', icon: Calendar },
    { name: 'AI Assistant', path: '/assistant', icon: MessageSquare },
    { name: 'User Profile', path: '/profile', icon: UserIcon },
  ];

  // Navigation for Admins
  const adminNavItems = [
    { name: 'Overview', path: '/admin', icon: LayoutDashboard },
    { name: 'User Management', path: '/admin/users', icon: Users },
    { name: 'Analytics', path: '/admin/analytics', icon: BarChart2 },
    { name: 'Settings', path: '/admin/settings', icon: Settings },
  ];

  const navItems = isAdmin ? adminNavItems : userNavItems;

  const handleLogout = () => {
    setUser({ currentUser: null, stats: {}, recentActivity: [] });
    navigate('/login');
  };

  const isAssistantPage = location.pathname === '/assistant';

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950 font-sans text-gray-800 dark:text-gray-100 relative transition-colors">
      
      {/* Sidebar */}
      <div className="w-64 text-white flex flex-col justify-between bg-[#0f172a] z-20">
        <div>
          <div className="flex items-center gap-3 p-6">
            <Shield className={`w-8 h-8 ${isAdmin ? 'text-red-500' : 'text-blue-500'}`} />
            <div>
              <h1 className="text-xl font-bold tracking-wide">{isAdmin ? 'Admin Portal' : 'AI Medical Legal Analyser'}</h1>
              {isAdmin && <p className="text-xs text-slate-400">AI Medical Legal Analyser</p>}
            </div>
          </div>
          <nav className="mt-4">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link 
                  key={item.name} 
                  to={item.path}
                  className={`flex items-center gap-3 px-6 py-3 mx-4 rounded-lg transition-colors ${
                    isActive 
                      ? (isAdmin ? 'bg-red-500/10 text-red-500 border border-red-500/20' : 'bg-blue-600 text-white') 
                      : 'text-gray-400 hover:text-white hover:bg-gray-800'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="p-6">
          <button onClick={handleLogout} className="flex items-center gap-3 text-gray-400 hover:text-white transition-colors w-full">
            <LogOut className="w-5 h-5" />
            <span className="font-medium">Sign Out</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden z-10 min-h-0">
        
        {/* Top Navigation */}
        <header className="bg-white dark:bg-gray-900 h-auto min-h-[4rem] border-b border-gray-200 dark:border-gray-800 flex items-center justify-end px-8 py-3 transition-colors">
          <div className="flex items-start gap-3">
            {currentUser.avatar_url ? (
              <img
                src={`${API_URL}${currentUser.avatar_url}`}
                alt=""
                className="w-8 h-8 shrink-0 rounded-full object-cover ring-2 ring-white dark:ring-gray-800"
              />
            ) : (
              <div className={`w-8 h-8 shrink-0 rounded-full flex items-center justify-center font-bold ${isAdmin ? 'bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-400' : 'bg-blue-100 text-blue-600 dark:bg-blue-950 dark:text-blue-400'}`}>
                {currentUser.initials}
              </div>
            )}
            <div className="flex flex-col items-end gap-1.5 text-right">
              <div className="text-sm">
                <p className="font-bold text-gray-800 dark:text-gray-100 leading-tight">{currentUser.name}</p>
                <p className="text-gray-500 dark:text-gray-400 text-xs">{currentUser.role}</p>
              </div>
              <button
                type="button"
                onClick={toggleDarkMode}
                className="mt-2 inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white transition-colors"
                aria-pressed={darkMode}
                aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {darkMode ? (
                  <>
                    <Sun className="w-3.5 h-3.5" />
                    <span>Light mode</span>
                  </>
                ) : (
                  <>
                    <Moon className="w-3.5 h-3.5" />
                    <span>Dark mode</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </header>

        <main
          className={
            isAssistantPage
              ? 'flex-1 flex flex-col min-h-0 overflow-hidden p-0 dark:bg-gray-950'
              : 'flex-1 overflow-y-auto p-8 dark:bg-gray-950'
          }
        >
          {children}
        </main>
      </div>

    </div>
  );
};

export default Layout;