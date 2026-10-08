// frontend/src/context/UserContext.jsx
import React, { createContext, useState, useContext } from 'react';

// Create the context
const UserContext = createContext(null);

// Create a provider component
export const UserProvider = ({ children }) => {
  // SIMULATED LOGIN STATE:
  // In the future, this data will come from your backend FastAPI login endpoint.
  // For now, we set up the structure for a logged-in user with empty data.
  const [user, setUser] = useState({
    currentUser: null,
    stats: {
      docsAnalyzed: 0,
      avgRiskScore: 'N/A',
      clausesDetected: 0,
      upcomingDeadlines: 0,
    },
    recentActivity: [],
  });

  return (
    <UserContext.Provider value={{ user, setUser }}>
      {children}
    </UserContext.Provider>
  );
};

// Custom hook to make using the context easier
export const useUser = () => {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
};