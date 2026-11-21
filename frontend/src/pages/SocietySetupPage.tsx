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
 * Redesigned in warm Pinterest-inspired lifestyle palette.
 */
export const SocietySetupPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, register, createSociety, joinSociety } = useApp();

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
  const [joinRole, setJoinRole] = useState<'resident' | 'volunteer'>('resident');

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
          role: joinRole,
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
    if (mode === 'create' || joinRole === 'volunteer') {
      navigate('/volunteer');
    } else {
      navigate('/resident');
    }
  };

  if (isSuccess && createdSociety) {
    return (
      <Card className="text-center p-8 sm:p-10 space-y-5 max-w-md mx-auto bg-white border-[#EBE8DF] shadow-lifted">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-[#EBF2EE] text-[#174D3A] border border-[#174D3A]/20 shadow-xs">
          <CheckCircle2 className="h-8 w-8" />
        </div>
        <h2 className="text-2xl font-bold text-[#252824] tracking-tight">
          {mode === 'create' ? 'Society Created Successfully!' : 'Joined Society Successfully!'}
        </h2>
        <p className="text-xs sm:text-sm text-[#827F76] leading-relaxed">
          {mode === 'create' ? (
            <>
              Your community <span className="font-bold text-[#252824]">"{createdSociety.name}"</span> is ready.
              You have been registered as <span className="font-bold text-[#174D3A]">Flat {confirmedFlat} (Admin)</span>.
            </>
          ) : (
            <>
              You are now registered as a resident of <span className="font-bold text-[#252824]">Flat {confirmedFlat}</span> in{' '}
              <span className="font-bold text-[#174D3A]">{createdSociety.name}</span>.
            </>
          )}
        </p>

        {/* Invite Code Box for Creator */}
        {mode === 'create' && (
          <div className="rounded-2xl border border-dashed border-[#174D3A]/40 bg-[#FAF9F6] p-4 space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#174D3A] block">Society Invite Code</span>
            <div className="flex items-center justify-center gap-2">
              <span className="text-xl font-mono font-black text-[#252824] tracking-widest">
                {createdSociety.invite_code}
              </span>
              <button
                type="button"
                onClick={handleCopyInviteCode}
                className="flex items-center gap-1 rounded-xl bg-white px-2.5 py-1 text-xs font-semibold text-[#174D3A] border border-[#DFDAD0] hover:bg-[#EBF2EE] transition-colors shadow-xs"
              >
                {copiedCode ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                <span>{copiedCode ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <p className="text-[11px] text-[#827F76]">
              Share this invite code with apartment neighbors to pool orders in bulk.
            </p>
          </div>
        )}

        <div className="pt-2">
          <Button variant="primary" size="md" className="w-full shadow-md shadow-[#174D3A]/20" onClick={handleFinish}>
            Enter Society Dashboard
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back to home */}
      <button
        type="button"
        onClick={() => navigate('/')}
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#827F76] hover:text-[#252824] transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        <span>Back to Home</span>
      </button>

      {/* Mode Switcher Tabs */}
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={() => {
            setMode('create');
            setError('');
          }}
          className={`flex items-center justify-center gap-2 rounded-2xl p-3.5 text-xs font-bold transition-all border ${
            mode === 'create'
              ? 'border-[#174D3A] bg-[#EBF2EE] text-[#174D3A] shadow-xs'
              : 'border-[#DFDAD0] bg-white text-[#827F76] hover:bg-[#FAF9F6]'
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
          className={`flex items-center justify-center gap-2 rounded-2xl p-3.5 text-xs font-bold transition-all border ${
            mode === 'join'
              ? 'border-[#174D3A] bg-[#EBF2EE] text-[#174D3A] shadow-xs'
              : 'border-[#DFDAD0] bg-white text-[#827F76] hover:bg-[#FAF9F6]'
          }`}
        >
          <Users className="h-4 w-4" />
          <span>Join with Code</span>
        </button>
      </div>

      {/* Form Card */}
      <Card className="p-6 sm:p-8 bg-white border-[#EBE8DF] shadow-card">
        <div className="mb-6">
          <h2 className="text-xl font-bold text-[#252824] tracking-tight">
            {mode === 'create' ? 'Create a Society Group' : 'Join Existing Apartment'}
          </h2>
          <p className="text-xs sm:text-sm text-[#827F76] mt-1">
            {mode === 'create'
              ? 'Set up your apartment community to begin coordinating group orders.'
              : 'Enter the invite code shared by your society volunteer or neighbor.'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* User Account Fields (if user is not authenticated yet) */}
          {!isAuthenticated && (
            <div className="p-4 rounded-2xl bg-[#FAF9F6] border border-[#EBE8DF] space-y-3 mb-2">
              <span className="text-xs font-bold text-[#252824] block">Your Account Details</span>
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
                leftIcon={<KeyRound className="h-4 w-4 text-[#827F76]" />}
              />

              <Input
                label="Your Flat Number"
                value={joinFlat}
                onChange={(e) => setJoinFlat(e.target.value)}
                placeholder="e.g. C-402 or B-104"
                required
              />

              <div className="space-y-2 pt-1">
                <label className="block text-xs font-bold text-[#252824]">
                  Select Your Role in this Society
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <button
                    type="button"
                    onClick={() => setJoinRole('resident')}
                    className={`flex flex-col text-left p-3 rounded-2xl border transition-all ${
                      joinRole === 'resident'
                        ? 'border-[#174D3A] bg-[#EBF2EE] ring-2 ring-[#174D3A]/15'
                        : 'border-[#EBE8DF] bg-[#FAF9F6] hover:bg-white'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-[#252824]">Resident</span>
                      <span className={`h-2.5 w-2.5 rounded-full ${joinRole === 'resident' ? 'bg-[#174D3A]' : 'bg-[#DFDAD0]'}`} />
                    </div>
                    <p className="text-[11px] text-[#827F76] leading-tight">
                      Submit grocery needs in chat, join bulk wholesale orders, and view itemized bills.
                    </p>
                  </button>

                  <button
                    type="button"
                    onClick={() => setJoinRole('volunteer')}
                    className={`flex flex-col text-left p-3 rounded-2xl border transition-all ${
                      joinRole === 'volunteer'
                        ? 'border-[#174D3A] bg-[#EBF2EE] ring-2 ring-[#174D3A]/15'
                        : 'border-[#EBE8DF] bg-[#FAF9F6] hover:bg-white'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-[#252824]">Volunteer</span>
                      <span className={`h-2.5 w-2.5 rounded-full ${joinRole === 'volunteer' ? 'bg-[#174D3A]' : 'bg-[#DFDAD0]'}`} />
                    </div>
                    <p className="text-[11px] text-[#827F76] leading-tight">
                      Manage order drives, compile shopping lists, and execute shopping runs. (Limit 1).
                    </p>
                  </button>
                </div>
              </div>
            </>
          )}

          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 font-semibold">
              {error}
            </div>
          )}

          <Button type="submit" variant="primary" className="w-full mt-2 shadow-sm shadow-[#174D3A]/20" isLoading={isLoading}>
            {mode === 'create' ? 'Create Society & Generate Code' : 'Join Society'}
          </Button>
        </form>
      </Card>
    </div>
  );
};
