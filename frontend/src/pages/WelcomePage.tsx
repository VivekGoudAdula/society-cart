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
  UserPlus,
  LogIn,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Input } from '../components/common/Input';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';

type AuthMode = 'login' | 'register';

/**
 * Screen 1: Welcome & Authentication experience with Sign In, Registration,
 * and quick demo portals for hackathon review.
 */
export const WelcomePage: React.FC = () => {
  const navigate = useNavigate();
  const { login, register, switchRole } = useApp();

  const [authMode, setAuthMode] = useState<AuthMode>('login');

  // Sign In state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Register state
  const [registerName, setRegisterName] = useState('');
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPhone, setRegisterPhone] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');

  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  /**
   * Handles user login submission.
   */
  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email.trim()) {
      setError('Please enter your email address.');
      return;
    }
    if (!password.trim() || password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setIsLoading(true);
    const result = await login(email.trim(), password);
    setIsLoading(false);

    if (!result.success) {
      setError(result.error || 'Invalid email or password.');
      return;
    }

    // Redirect to dashboard or society setup
    navigate('/resident');
  };

  /**
   * Handles user registration submission.
   */
  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!registerName.trim()) {
      setError('Please enter your full name.');
      return;
    }
    if (!registerEmail.trim()) {
      setError('Please enter your email address.');
      return;
    }
    if (!registerPassword.trim() || registerPassword.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setIsLoading(true);
    const result = await register(
      registerName.trim(),
      registerEmail.trim(),
      registerPassword,
      registerPhone.trim() || undefined
    );
    setIsLoading(false);

    if (!result.success) {
      setError(result.error || 'Registration failed.');
      return;
    }

    // New user has no society yet — take them directly to society setup
    navigate('/society-setup');
  };

  /**
   * Instant demo access for reviewers without credentials.
   */
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
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#18231E]">
          Society Cart
        </h1>
        <p className="text-sm sm:text-base font-semibold text-[#23865B]">
          Your Society. One Chat. One Bulk Order.
        </p>
        <p className="max-w-md mx-auto text-xs sm:text-sm text-[#718078] leading-relaxed">
          Coordinate grocery buying with your apartment neighbors. Submit items in chat, pool orders in bulk, and save money through wholesale group buying.
        </p>
      </div>

      {/* Auth Card */}
      <Card className="p-6 sm:p-8">
        {/* Tab Switcher */}
        <div className="flex rounded-xl bg-slate-100 p-1 mb-6">
          <button
            type="button"
            onClick={() => {
              setAuthMode('login');
              setError('');
            }}
            className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-bold rounded-lg transition-all ${
              authMode === 'login'
                ? 'bg-white text-[#18231E] shadow-xs'
                : 'text-[#718078] hover:text-[#18231E]'
            }`}
          >
            <LogIn className="h-3.5 w-3.5" />
            <span>Sign In</span>
          </button>
          <button
            type="button"
            onClick={() => {
              setAuthMode('register');
              setError('');
            }}
            className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-bold rounded-lg transition-all ${
              authMode === 'register'
                ? 'bg-white text-[#18231E] shadow-xs'
                : 'text-[#718078] hover:text-[#18231E]'
            }`}
          >
            <UserPlus className="h-3.5 w-3.5" />
            <span>Create Account</span>
          </button>
        </div>

        {authMode === 'login' ? (
          /* Sign In Form */
          <form onSubmit={handleLoginSubmit} className="space-y-4">
            <Input
              label="Email Address"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. rahul.sharma@example.com"
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

            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-[#D9534F] font-semibold">
                {error}
              </div>
            )}

            <Button type="submit" variant="primary" className="w-full" isLoading={isLoading}>
              Sign In to My Society
            </Button>
          </form>
        ) : (
          /* Registration Form */
          <form onSubmit={handleRegisterSubmit} className="space-y-4">
            <Input
              label="Full Name"
              type="text"
              value={registerName}
              onChange={(e) => setRegisterName(e.target.value)}
              placeholder="e.g. Rahul Sharma"
              required
            />

            <Input
              label="Email Address"
              type="email"
              value={registerEmail}
              onChange={(e) => setRegisterEmail(e.target.value)}
              placeholder="e.g. rahul@example.com"
              required
            />

            <Input
              label="Phone Number (Optional)"
              type="tel"
              value={registerPhone}
              onChange={(e) => setRegisterPhone(e.target.value)}
              placeholder="e.g. +91 98765 43210"
            />

            <Input
              label="Password"
              type={showPassword ? 'text' : 'password'}
              value={registerPassword}
              onChange={(e) => setRegisterPassword(e.target.value)}
              placeholder="Choose a strong password (min 6 characters)"
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

            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-[#D9534F] font-semibold">
                {error}
              </div>
            )}

            <Button type="submit" variant="primary" className="w-full" isLoading={isLoading}>
              Create Account & Continue
            </Button>
          </form>
        )}

        {/* Create or Join Society link */}
        <div className="mt-4 pt-4 border-t border-[#E6ECE8] text-center">
          <p className="text-xs text-[#718078]">
            Already set up or have an invite code?{' '}
            <button
              onClick={() => navigate('/society-setup')}
              className="font-bold text-[#23865B] hover:underline focus:outline-none"
            >
              Set up or Join a Society
            </button>
          </p>
        </div>

        {/* Quick Demo Access Buttons for Hackathon Evaluators */}
        <div className="mt-6 pt-5 border-t border-[#E6ECE8] bg-[#F8FAF9] -mx-6 sm:-mx-8 -mb-6 sm:-mb-8 p-5 sm:p-6 rounded-b-2xl">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-[#23865B]" /> Instant Demo Mode (Evaluator Sandbox)
            </span>
            <span className="text-[10px] text-slate-400">Pre-seeded demo</span>
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
