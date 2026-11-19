import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2,
  Users,
  ArrowLeft,
  CheckCircle2,
  KeyRound,
  Check,
  Copy,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Input } from '../components/common/Input';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { ApiSociety } from '../types';

type SetupMode = 'create' | 'join';

/**
 * Screen 2: Create or Join an Apartment Society flow backed by real backend APIs.
 */
export const SocietySetupPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, register, createSociety, joinSociety, switchRole } = useApp();

  const [mode, setMode] = useState<SetupMode>('create');
  const [isSuccess, setIsSuccess] = useState(false);
  const [createdSociety, setCreatedSociety] = useState<ApiSociety | null>(null);
  const [confirmedFlat, setConfirmedFlat] = useState('');
  const [copiedCode, setCopiedCode] = useState(false);

  // Form State: Create
  const [societyName, setSocietyName] = useState('Greenfield Heights Residency');
  const [address, setAddress] = useState('Plot 42, Hitec City Road');
  const [city, setCity] = useState('Hyderabad');
  const [totalFlats, setTotalFlats] = useState('128');
  const [creatorFlat, setCreatorFlat] = useState('C-402');

  // Form State: Join
  const [inviteCode, setInviteCode] = useState('');
  const [joinFlat, setJoinFlat] = useState('');

  // Form State: Auth if not logged in
  const [authName, setAuthName] = useState('');
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');

  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  /**
   * Handles creation or joining of an apartment society.
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      // If user is not yet logged in, create their account first
      if (!isAuthenticated) {
        if (!authName.trim() || !authEmail.trim() || !authPassword.trim()) {
          setError('Please provide your name, email, and password to create an account.');
          setIsLoading(false);
          return;
        }
        const regRes = await register(authName.trim(), authEmail.trim(), authPassword);
        if (!regRes.success) {
          setError(regRes.error || 'Failed to create user account.');
          setIsLoading(false);
          return;
        }
      }

      if (mode === 'create') {
        if (!societyName.trim() || !address.trim() || !city.trim() || !creatorFlat.trim()) {
          setError('Please complete all required society fields.');
          setIsLoading(false);
          return;
        }

        const res = await createSociety({
          name: societyName.trim(),
          address: address.trim(),
          city: city.trim(),
          country: 'India',
          total_flats: totalFlats ? parseInt(totalFlats, 10) : undefined,
          creator_flat_number: creatorFlat.trim(),
        });

        if (!res.success || !res.society) {
          setError(res.error || 'Failed to create society.');
          setIsLoading(false);
          return;
        }

        setCreatedSociety(res.society);
        setConfirmedFlat(creatorFlat.trim());
        setIsSuccess(true);
      } else {
        if (!inviteCode.trim() || !joinFlat.trim()) {
          setError('Please enter the society invite code and your flat number.');
          setIsLoading(false);
          return;
        }

        const res = await joinSociety({
          invite_code: inviteCode.trim(),
          flat_number: joinFlat.trim(),
        });

        if (!res.success || !res.society) {
          setError(res.error || 'Failed to join society.');
          setIsLoading(false);
          return;
        }

        setCreatedSociety(res.society);
        setConfirmedFlat(joinFlat.trim());
        setIsSuccess(true);
      }
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyInviteCode = () => {
    if (createdSociety?.invite_code) {
      navigator.clipboard.writeText(createdSociety.invite_code);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    }
  };

  const handleFinish = () => {
    switchRole(mode === 'create' ? 'volunteer' : 'resident');
    navigate(mode === 'create' ? '/volunteer' : '/resident');
  };

  if (isSuccess && createdSociety) {
    return (
      <Card className="text-center p-8 space-y-4 max-w-md mx-auto">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 border border-emerald-100">
          <CheckCircle2 className="h-8 w-8" />
        </div>
        <h2 className="text-xl font-bold text-[#18231E]">
          {mode === 'create' ? 'Society Created Successfully!' : 'Joined Society Successfully!'}
        </h2>
        <p className="text-xs text-[#718078] leading-relaxed">
          {mode === 'create' ? (
            <>
              Your community <span className="font-bold text-[#18231E]">"{createdSociety.name}"</span> is set up.
              You have been registered as <span className="font-bold text-[#18231E]">Flat {confirmedFlat} (Admin)</span>.
            </>
          ) : (
            <>
              You are now registered as a resident of <span className="font-bold text-[#18231E]">Flat {confirmedFlat}</span> in{' '}
              <span className="font-bold text-[#18231E]">{createdSociety.name}</span>.
            </>
          )}
        </p>

        {/* Invite Code Box for Creator */}
        {mode === 'create' && (
          <div className="rounded-xl border border-dashed border-[#23865B] bg-[#EAF5EE]/40 p-4 space-y-2">
            <span className="text-[11px] font-semibold text-[#196B48] block">Society Invite Code</span>
            <div className="flex items-center justify-center gap-2">
              <span className="text-lg font-mono font-black text-[#18231E] tracking-widest">
                {createdSociety.invite_code}
              </span>
              <button
                type="button"
                onClick={handleCopyInviteCode}
                className="flex items-center gap-1 rounded-lg bg-white px-2.5 py-1 text-xs font-semibold text-[#23865B] border border-[#23865B]/30 hover:bg-[#EAF5EE] transition-colors"
              >
                {copiedCode ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                <span>{copiedCode ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <p className="text-[10px] text-[#718078]">
              Share this code with your apartment neighbors so they can join this group order.
            </p>
          </div>
        )}

        <div className="pt-4">
          <Button variant="primary" className="w-full" onClick={handleFinish}>
            Enter Society Dashboard
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back to login */}
      <button
        type="button"
        onClick={() => navigate('/')}
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#718078] hover:text-[#18231E] transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        <span>Back to Login</span>
      </button>

      {/* Mode Switcher Tabs */}
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={() => {
            setMode('create');
            setError('');
          }}
          className={`flex items-center justify-center gap-2 rounded-xl p-3.5 text-xs font-bold transition-all border ${
            mode === 'create'
              ? 'border-[#23865B] bg-[#EAF5EE] text-[#196B48] shadow-xs'
              : 'border-[#E6ECE8] bg-white text-[#718078] hover:bg-slate-50'
          }`}
        >
          <Building2 className="h-4 w-4" />
          <span>Create New Society</span>
        </button>

        <button
          type="button"
          onClick={() => {
            setMode('join');
            setError('');
          }}
          className={`flex items-center justify-center gap-2 rounded-xl p-3.5 text-xs font-bold transition-all border ${
            mode === 'join'
              ? 'border-[#23865B] bg-[#EAF5EE] text-[#196B48] shadow-xs'
              : 'border-[#E6ECE8] bg-white text-[#718078] hover:bg-slate-50'
          }`}
        >
          <Users className="h-4 w-4" />
          <span>Join with Code</span>
        </button>
      </div>

      {/* Form Card */}
      <Card className="p-6 sm:p-8">
        <div className="mb-6">
          <h2 className="text-lg font-bold text-[#18231E]">
            {mode === 'create' ? 'Create a Society Group' : 'Join Existing Apartment'}
          </h2>
          <p className="text-xs text-[#718078] mt-1">
            {mode === 'create'
              ? 'Set up your apartment community to begin coordinating group orders.'
              : 'Enter the invite code shared by your society volunteer or neighbor.'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* User Account Fields (if user is not authenticated yet) */}
          {!isAuthenticated && (
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3 mb-2">
              <span className="text-xs font-bold text-[#18231E] block">Your Account Details</span>
              <Input
                label="Your Full Name"
                value={authName}
                onChange={(e) => setAuthName(e.target.value)}
                placeholder="e.g. Rahul Sharma"
                required
              />
              <Input
                label="Your Email"
                type="email"
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                placeholder="e.g. rahul@example.com"
                required
              />
              <Input
                label="Create Password"
                type="password"
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                placeholder="Min 6 characters"
                required
              />
            </div>
          )}

          {mode === 'create' ? (
            <>
              <Input
                label="Society / Apartment Name"
                value={societyName}
                onChange={(e) => setSocietyName(e.target.value)}
                placeholder="e.g. Greenfield Heights"
                required
              />

              <Input
                label="Address / Locality"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="e.g. Plot 42, Hitec City Road"
                required
              />

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Input
                  label="City"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="e.g. Hyderabad"
                  required
                />
                <Input
                  label="Total Flats (Optional)"
                  type="number"
                  value={totalFlats}
                  onChange={(e) => setTotalFlats(e.target.value)}
                  placeholder="e.g. 128"
                />
              </div>

              <Input
                label="Your Flat Number"
                value={creatorFlat}
                onChange={(e) => setCreatorFlat(e.target.value)}
                placeholder="e.g. C-402"
                required
              />
            </>
          ) : (
            <>
              <Input
                label="Society Invite Code"
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
                placeholder="e.g. SC-A8F2 or GFH-2026"
                required
                leftIcon={<KeyRound className="h-4 w-4 text-[#718078]" />}
              />

              <Input
                label="Your Flat Number"
                value={joinFlat}
                onChange={(e) => setJoinFlat(e.target.value)}
                placeholder="e.g. C-402 or B-104"
                required
              />
            </>
          )}

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-[#D9534F] font-semibold">
              {error}
            </div>
          )}

          <Button type="submit" variant="primary" className="w-full" isLoading={isLoading}>
            {mode === 'create' ? 'Create Society & Generate Code' : 'Join Society'}
          </Button>
        </form>
      </Card>
    </div>
  );
};
