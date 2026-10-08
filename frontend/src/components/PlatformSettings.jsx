import React, { useState } from 'react';
import { Settings, Save } from 'lucide-react';

const PlatformSettings = () => {
  const [formData, setFormData] = useState({
    platformName: 'AI Legal Analyzer',
    maxUploadSize: '25',
    adminEmail: 'admin@legalanalyzer.com'
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSave = (e) => {
    e.preventDefault();
    alert("Settings saved successfully!");
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in text-gray-800">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Platform Settings</h1>
        <p className="text-gray-500 mt-1">Configure platform-wide settings and preferences.</p>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-8">
        <h2 className="text-lg font-bold mb-6 flex items-center gap-2 text-slate-800">
          <Settings className="w-5 h-5" /> Platform Settings
        </h2>
        
        <form onSubmit={handleSave} className="space-y-6 max-w-lg">
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2">Platform Name</label>
            <input 
              type="text" 
              name="platformName"
              value={formData.platformName}
              onChange={handleChange}
              className="block w-full px-4 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition-all text-slate-700" 
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2">Max Upload Size (MB)</label>
            <input 
              type="number" 
              name="maxUploadSize"
              value={formData.maxUploadSize}
              onChange={handleChange}
              className="block w-full px-4 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition-all text-slate-700" 
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2">Admin Contact Email</label>
            <input 
              type="email" 
              name="adminEmail"
              value={formData.adminEmail}
              onChange={handleChange}
              className="block w-full px-4 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition-all text-slate-700" 
            />
          </div>

          <button 
            type="submit" 
            className="flex items-center gap-2 bg-[#ef4444] hover:bg-red-600 text-white px-6 py-2.5 rounded-lg font-bold transition-colors"
          >
            <Save className="w-4 h-4" /> Save Settings
          </button>
        </form>
      </div>
    </div>
  );
};

export default PlatformSettings;