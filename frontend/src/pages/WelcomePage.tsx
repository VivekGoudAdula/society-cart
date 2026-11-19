import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShoppingCart,
  Eye,
  EyeOff,
  ArrowRight,
  Sparkles,
  ShieldCheck,
  User,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Input } from '../components/common/Input';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';

/**
 * Screen 1: Welcome & Login experience with role demo portals and 3-step value workflow.
 */
export const WelcomePage: React.FC = () => {
  const navigate = useNavigate();
  const { switchRole } = useApp();

  const [identifier, setIdentifier] = useState('rahul.sharma@example.com');
  const [password, setPassword] = useState('demo1234');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!identifier.trim()) {
      setError('Please enter your email or phone number.');
      return;
    }
    if (!password.trim() || password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      // If logging in with volunteer email, route to volunteer
      if (identifier.toLowerCase().includes('volunteer') || identifier.toLowerCase().includes('priya')) {
        switchRole('volunteer');
        navigate('/volunteer');
      } else {
        switchRole('resident');
        navigate('/resident');
      }
    }, 400);
  };

  const handleDemoAccess = (role: 'resident' | 'volunteer') => {
    switchRole(role);
    if (role === 'resident') {
      navigate('/resident');
    } else {
      navigate('/volunteer');
    }
  };

  return (
    <div className="space-y-8">
      {/* Hero Branding Card */}
      <div className="text-center space-y-3">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#23865B] text-white shadow-md shadow-[#23865B]/20">
          <ShoppingCart className="h-7 w-7" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#18231E]">Society Cart</h1>
        <p className="text-sm sm:text-base font-semibold text-[#23865B]">
          Your Society. One Chat. One Bulk Order.
        </p>
        <p className="max-w-md mx-auto text-xs sm:text-sm text-[#718078] leading-relaxed">
          Coordinate grocery buying with your neighbors in a single group chat. Volunteers buy in bulk at wholesale rates, saving money and hassle for everyone.
        </p>
      </div>

      {/* Login & Demo Selection Card */}
      <Card className="p-6 sm:p-8">
        <form onSubmit={handleLoginSubmit} className="space-y-4">
          <Input
            label="Email or Mobile Number"
            type="text"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="e.g. rahul@example.com or 9876543210"
            required
          />

          <Input
            label="Password"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
            required
            rightIcon={
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="text-slate-400 hover:text-slate-600 focus:outline-none"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            }
          />

          {error && <p className="text-xs text-[#D9534F] font-semibold">{error}</p>}

          <Button type="submit" variant="primary" className="w-full" isLoading={isLoading}>
            Sign In to My Society
          </Button>
        </form>

        {/* Create or Join Society link */}
        <div className="mt-4 pt-4 border-t border-[#E6ECE8] text-center">
          <p className="text-xs text-[#718078]">
            New society or resident?{' '}
            <button
              onClick={() => navigate('/society-setup')}
              className="font-bold text-[#23865B] hover:underline focus:outline-none"
            >
              Create or Join a Society
            </button>
          </p>
        </div>

        {/* Quick Demo Access Buttons for Hackathon Evaluators */}
        <div className="mt-6 pt-5 border-t border-[#E6ECE8] bg-[#F8FAF9] -mx-6 sm:-mx-8 -mb-6 sm:-mb-8 p-5 sm:p-6 rounded-b-2xl">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-[#23865B]" /> Instant Demo Mode (Phase 1 Prototype)
            </span>
            <span className="text-[10px] text-slate-400">Simulated state</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => handleDemoAccess('resident')}
              className="flex items-center gap-3 p-3 rounded-xl border border-[#E6ECE8] bg-white hover:border-[#23865B] hover:shadow-xs text-left transition-all group"
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#EAF5EE] text-[#196B48]">
                <User className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <span className="text-xs font-bold text-[#18231E] block group-hover:text-[#23865B]">
                  Resident Demo
                </span>
                <span className="text-[11px] text-[#718078] block truncate">Rahul (Flat C-402)</span>
              </div>
              <ArrowRight className="h-4 w-4 text-slate-400 group-hover:translate-x-0.5 group-hover:text-[#23865B] transition-all" />
            </button>

            <button
              type="button"
              onClick={() => handleDemoAccess('volunteer')}
              className="flex items-center gap-3 p-3 rounded-xl border border-[#E6ECE8] bg-white hover:border-[#23865B] hover:shadow-xs text-left transition-all group"
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <span className="text-xs font-bold text-[#18231E] block group-hover:text-[#23865B]">
                  Volunteer Demo
                </span>
                <span className="text-[11px] text-[#718078] block truncate">Priya (Flat B-204)</span>
              </div>
              <ArrowRight className="h-4 w-4 text-slate-400 group-hover:translate-x-0.5 group-hover:text-[#23865B] transition-all" />
            </button>
          </div>
        </div>
      </Card>

      {/* 3-Step Process Explanation */}
      <div className="space-y-3 pt-2">
        <h3 className="text-xs font-bold uppercase tracking-wider text-center text-[#718078]">
          How Society Cart Works
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="rounded-xl border border-[#E6ECE8] bg-white p-4 text-center">
            <div className="mx-auto flex h-9 w-9 items-center justify-center rounded-lg bg-[#EAF5EE] text-[#196B48] mb-2 font-bold text-xs">
              1
            </div>
            <h4 className="text-xs font-bold text-[#18231E]">Share in Chat</h4>
            <p className="mt-1 text-[11px] text-[#718078] leading-snug">
              Residents text grocery needs in plain language (English, Telugu, Hindi).
            </p>
          </div>

          <div className="rounded-xl border border-[#E6ECE8] bg-white p-4 text-center">
            <div className="mx-auto flex h-9 w-9 items-center justify-center rounded-lg bg-[#EAF5EE] text-[#196B48] mb-2 font-bold text-xs">
              2
            </div>
            <h4 className="text-xs font-bold text-[#18231E]">Bulk Consolidation</h4>
            <p className="mt-1 text-[11px] text-[#718078] leading-snug">
              Items are tallied into a master shopping list for a volunteer to buy at wholesale prices.
            </p>
          </div>

          <div className="rounded-xl border border-[#E6ECE8] bg-white p-4 text-center">
            <div className="mx-auto flex h-9 w-9 items-center justify-center rounded-lg bg-[#EAF5EE] text-[#196B48] mb-2 font-bold text-xs">
              3
            </div>
            <h4 className="text-xs font-bold text-[#18231E]">Delivery & Savings</h4>
            <p className="mt-1 text-[11px] text-[#718078] leading-snug">
              Groceries arrive at your door with transparent bills and recorded savings.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
