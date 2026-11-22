import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Analytics } from '@vercel/analytics/react';
import { AppProvider } from './context/AppContext';
import { ChatProvider } from './context/ChatContext';
import { AuthLayout } from './layouts/AuthLayout';
import { AppLayout } from './layouts/AppLayout';
import { WelcomePage } from './pages/WelcomePage';
import { SocietySetupPage } from './pages/SocietySetupPage';
import { ResidentDashboard } from './pages/ResidentDashboard';
import { VolunteerDashboard } from './pages/VolunteerDashboard';
import { SocietyChatPage } from './pages/SocietyChatPage';
import { ShoppingListPage } from './pages/ShoppingListPage';
import { OrderSummaryPage } from './pages/OrderSummaryPage';

/**
 * Root Application Component with Complete Routing Architecture.
 * Supports all 7 screens with role-based navigation and demo toggles.
 */
export default function App(): React.JSX.Element {
  return (
    <AppProvider>
      <ChatProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Landing Page (Full-Width Editorial Lifestyle UI) */}
            <Route path="/" element={<WelcomePage />} />

            {/* Society Setup / Onboarding Flow */}
            <Route element={<AuthLayout />}>
              <Route path="/society-setup" element={<SocietySetupPage />} />
            </Route>

            {/* Main Society Application Pages */}
            <Route element={<AppLayout />}>
              <Route path="/resident" element={<ResidentDashboard />} />
              <Route path="/volunteer" element={<VolunteerDashboard />} />
              <Route path="/chat" element={<SocietyChatPage />} />
              <Route path="/shopping-list" element={<ShoppingListPage />} />
              <Route path="/order-summary" element={<OrderSummaryPage />} />
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <Analytics />
        </BrowserRouter>
      </ChatProvider>
    </AppProvider>
  );
}
