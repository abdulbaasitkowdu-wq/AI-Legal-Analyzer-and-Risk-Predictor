import React, { useState, useEffect, useLayoutEffect } from 'react';
import { Mail, Lock, User, Shield, ArrowLeft, CheckCircle, MessageSquare, Calendar, Users, BarChart } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useUser } from '../context/UserContext';
import { useTheme } from '../context/ThemeContext.jsx';

const Auth = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [isAdminMode, setIsAdminMode] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  
  // Controlled form inputs
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');

  const navigate = useNavigate();
  const { user, setUser } = useUser();
  const { darkMode } = useTheme();

  /* Login route always renders in light mode; restore saved theme when leaving. */
  useLayoutEffect(() => {
    document.documentElement.classList.remove('dark');
    return () => {
      if (darkMode) {
        document.documentElement.classList.add('dark');
      }
    };
  }, [darkMode]);

  useEffect(() => {
    if (!user?.currentUser) return;
    const role = user.currentUser.role;
    const isAdmin = role === 'Admin' || role === 'Super Admin';
    navigate(isAdmin ? '/admin' : '/', { replace: true });
  }, [user?.currentUser, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

    try {
      if (isLogin || isAdminMode) {
        // --- REAL LOGIN LOGIC ---
        const response = await axios.post(`${API_URL}/api/login`, {
          email: email,
          password: password,
          is_admin: isAdminMode
        });
        
        // Update global context ONLY on successful login
        setUser({
          currentUser: response.data.user,
          stats: { docsAnalyzed: 0, avgRiskScore: 'N/A', clausesDetected: 0, upcomingDeadlines: 0 },
          recentActivity: []
        });

        // Redirect to dashboard
        if (isAdminMode) {
          navigate('/admin'); 
        } else {
          navigate('/');
        }

      } else {
       
        await axios.post(`${API_URL}/api/register`, {
          name: name,
          email: email,
          password: password
        });
        
        alert("Account created successfully! Please sign in to continue.");
        setPassword('');
        setIsLogin(true);
      }

    } catch (error) {
      alert(error.response?.data?.detail || "An error occurred connecting to the server.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex font-sans">
      
      {/* LEFT PANEL - Dynamic Dark Section */}
      <div className="hidden lg:flex lg:w-1/2 bg-[#0f172a] text-white p-16 flex-col justify-between relative overflow-hidden">
        {/* Subtle background grid pattern */}
        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(#ffffff 1px, transparent 1px)', backgroundSize: '30px 30px' }}></div>
        
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-12">
            <div className={`p-2 rounded-lg ${isAdminMode ? 'bg-red-500/20' : 'bg-blue-500'}`}>
              <Shield className={`w-6 h-6 ${isAdminMode ? 'text-red-500' : 'text-white'}`} />
            </div>
            <span className="font-bold tracking-wide">AI Legal Analyzer</span>
          </div>

          {!isAdminMode ? (
            // USER INFO
            <div className="space-y-8 max-w-lg">
              <h1 className="text-5xl font-extrabold leading-tight">AI Legal Analyzer <br/> & Risk Predictor</h1>
              <p className="text-slate-400 text-lg">Upload complex contracts. Understand hidden risks. Make informed decisions.</p>
              
              <div className="space-y-6 mt-12">
                <div className="flex items-start gap-4">
                  <div className="p-2 bg-slate-800 rounded-lg"><CheckCircle className="w-5 h-5 text-emerald-400" /></div>
                  <div>
                    <h3 className="font-bold text-white">Automated Risk Assessment</h3>
                    <p className="text-slate-400 text-sm">Low / Medium / High classification</p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <div className="p-2 bg-slate-800 rounded-lg"><MessageSquare className="w-5 h-5 text-blue-400" /></div>
                  <div>
                    <h3 className="font-bold text-white">Simple Clause Explanations</h3>
                    <p className="text-slate-400 text-sm">AI-powered plain English summaries</p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <div className="p-2 bg-slate-800 rounded-lg"><Calendar className="w-5 h-5 text-purple-400" /></div>
                  <div>
                    <h3 className="font-bold text-white">Google Calendar Deadline Sync</h3>
                    <p className="text-slate-400 text-sm">Never miss a critical date</p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            // ADMIN INFO
            <div className="space-y-8 max-w-lg">
              <h1 className="text-5xl font-extrabold leading-tight">Admin Portal</h1>
              <p className="text-slate-400 text-lg">Manage your platform, oversee user activity, and monitor document analytics from one control center.</p>
              
              <div className="space-y-6 mt-12">
                <div className="flex items-start gap-4">
                  <div className="p-2 bg-slate-800 rounded-lg"><Users className="w-5 h-5 text-red-400" /></div>
                  <div>
                    <h3 className="font-bold text-white">User Management</h3>
                    <p className="text-slate-400 text-sm">View and manage all user accounts, activity, and permissions.</p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <div className="p-2 bg-slate-800 rounded-lg"><BarChart className="w-5 h-5 text-red-400" /></div>
                  <div>
                    <h3 className="font-bold text-white">Platform Analytics</h3>
                    <p className="text-slate-400 text-sm">Track document uploads, risk scores, and usage trends.</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {!isAdminMode && (
          <div className="relative z-10 text-sm text-slate-500 font-medium">
            ⚖️ Trusted by 2,500+ legal professionals
          </div>
        )}
      </div>

      {/* RIGHT PANEL - Form Section */}
      <div className="w-full lg:w-1/2 bg-slate-50 flex items-center justify-center p-8 relative">
        <div className="w-full max-w-md">
          
          {isAdminMode && (
            <button onClick={() => setIsAdminMode(false)} className="flex items-center gap-2 text-slate-500 hover:text-slate-800 font-medium mb-8 transition-colors">
              <ArrowLeft className="w-4 h-4" /> Back to User Login
            </button>
          )}

          <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-8 sm:p-10">
            
            {isAdminMode ? (
              // ADMIN FORM
              <div className="text-center mb-8">
                <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Shield className="w-8 h-8 text-red-500" />
                </div>
                <h2 className="text-2xl font-bold text-slate-900">Admin Sign In</h2>
                <p className="text-slate-500 text-sm mt-1">Authorized personnel only</p>
              </div>
            ) : (
              // USER TOGGLE
              <div className="flex p-1 bg-slate-100 rounded-lg mb-8">
                <button 
                  type="button"
                  onClick={() => { setIsLogin(true); setPassword(''); }} 
                  className={`flex-1 py-2.5 text-sm font-bold rounded-md transition-all ${isLogin ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                >
                  Sign In
                </button>
                <button 
                  type="button"
                  onClick={() => { setIsLogin(false); setPassword(''); }} 
                  className={`flex-1 py-2.5 text-sm font-bold rounded-md transition-all ${!isLogin ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                >
                  Create Account
                </button>
              </div>
            )}

            <form className="space-y-5" onSubmit={handleSubmit}>
              {/* Full Name (Only for Registration) */}
              {!isLogin && !isAdminMode && (
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1.5">Full Name</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <User className="h-5 w-5 text-slate-400" />
                    </div>
                    <input 
                      type="text" 
                      required 
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="block w-full pl-10 pr-3 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition-all" 
                    />
                  </div>
                </div>
              )}

              {/* Email Address */}
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5">{isAdminMode ? 'Admin Email' : 'Email Address'}</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Mail className="h-5 w-5 text-slate-400" />
                  </div>
                  <input 
                    type="email" 
                    required 
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="block w-full pl-10 pr-3 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition-all" 
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5">Password</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-slate-400" />
                  </div>
                  <input 
                    type="password" 
                    required 
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={isAdminMode ? "Enter admin password" : "Enter your password"}
                    className="block w-full pl-10 pr-3 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition-all" 
                  />
                </div>
              </div>

              {/* Extras (Remember Me / Forgot Password) */}
              {!isAdminMode && isLogin && (
                <div className="flex items-center justify-between text-sm">
                  <label className="flex items-center gap-2 text-slate-500 cursor-pointer">
                    <input type="checkbox" className="rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
                    Remember me
                  </label>
                  <button type="button" className="font-bold text-blue-600 hover:text-blue-500">Forgot password?</button>
                </div>
              )}

              {/* Submit Button */}
              <button 
                type="submit" 
                disabled={isLoading}
                className={`w-full py-3 px-4 rounded-lg font-bold text-white transition-colors mt-2 disabled:opacity-70 ${isAdminMode ? 'bg-[#ef4444] hover:bg-red-600' : 'bg-[#3b82f6] hover:bg-blue-600'}`}
              >
                {isLoading 
                  ? 'Processing...' 
                  : (isAdminMode ? 'Sign In to Admin Portal' : (isLogin ? 'Sign In' : 'Create Account'))
                }
              </button>
            </form>
          </div>

          {/* Admin Toggle Link at Bottom */}
          {!isAdminMode && (
             <div className="text-center mt-8">
               <button type="button" onClick={() => { setIsAdminMode(true); setPassword(''); }} className="text-slate-500 text-sm font-medium hover:text-slate-800 underline decoration-slate-300 underline-offset-4">
                 Admin Login
               </button>
             </div>
          )}

        </div>
      </div>
    </div>
  );
};

export default Auth;