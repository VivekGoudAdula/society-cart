import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2,
  Users,
  ArrowLeft,
  CheckCircle2,
  KeyRound,
  Check,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Input } from '../components/common/Input';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';

type SetupMode = 'create' | 'join';

/**
 * Screen 2: Create or Join an Apartment Society flow with validation and simulated confirmation.
 */
export const SocietySetupPage: React.FC = () => {
  const navigate = useNavigate();
  const { switchRole } = useApp();

  const [mode, setMode] = useState<SetupMode>('create');
  const [isSuccess, setIsSuccess] = useState(false);

  // Form State: Create
  const [societyName, setSocietyName] = useState('Greenfield Heights Residency');
  const [locality, setLocality] = useState('Kondapur, Hitec City Road, Hyderabad');
  const [totalFlats, setTotalFlats] = useState('128');
  const [creatorName, setCreatorName] = useState('Rahul Sharma');
  const [creatorFlat, setCreatorFlat] = useState('C-402');

  // Form State: Join
  const [inviteCode, setInviteCode] = useState('GFH-2026');
  const [joinName, setJoinName] = useState('Rahul Sharma');
  const [joinFlat, setJoinFlat] = useState('C-402');

  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (mode === 'create') {
      if (!societyName.trim() || !locality.trim() || !creatorName.trim() || !creatorFlat.trim()) {
        setError('Please complete all required fields.');
        return;
      }
    } else {
      if (!inviteCode.trim() || !joinName.trim() || !joinFlat.trim()) {
        setError('Please enter the invite code, your name, and flat number.');
        return;
      }
    }

    setIsSuccess(true);
  };

  const handleFinish = () => {
    switchRole('resident');
    navigate('/resident');
  };

  if (isSuccess) {
    return (
      <Card className="text-center p-8 space-y-4 max-w-md mx-auto">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 border border-emerald-100">
          <CheckCircle2 className="h-8 w-8" />
        </div>
        <h2 className="text-xl font-bold text-[#18231E]">
          {mode === 'create' ? 'Society Created Successfully!' : 'Joined Society Successfully!'}
        </h2>
        <p className="text-xs text-[#718078] leading-relaxed">
          {mode === 'create'
            ? `Your society "${societyName}" is configured. Your invite code is GFH-2026. Share it with your apartment neighbors.`
            : `You are now registered as a resident of Flat ${joinFlat} in Greenfield Heights Residency.`}
        </p>

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

      <div>
        <h1 className="text-2xl font-bold text-[#18231E]">Get Started with Society Cart</h1>
        <p className="mt-1 text-xs text-[#718078]">
          Register a new apartment community or join your existing building's collective grocery group.
        </p>
      </div>

      {/* Mode Selection Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div
          onClick={() => setMode('create')}
          className={`p-4 rounded-2xl border cursor-pointer transition-all ${
            mode === 'create'
              ? 'border-[#23865B] bg-[#EAF5EE]/40 ring-2 ring-[#23865B]/20'
              : 'border-[#E6ECE8] bg-white hover:border-slate-300'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#EAF5EE] text-[#196B48]">
              <Building2 className="h-5 w-5" />
            </div>
            {mode === 'create' && <Check className="h-4 w-4 text-[#23865B]" />}
          </div>
          <h3 className="text-sm font-bold text-[#18231E]">Create a Society</h3>
          <p className="mt-1 text-[11px] text-[#718078] leading-snug">
            Set up a fresh community workspace and become the first coordinator.
          </p>
        </div>

        <div
          onClick={() => setMode('join')}
          className={`p-4 rounded-2xl border cursor-pointer transition-all ${
            mode === 'join'
              ? 'border-[#23865B] bg-[#EAF5EE]/40 ring-2 ring-[#23865B]/20'
              : 'border-[#E6ECE8] bg-white hover:border-slate-300'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100 text-slate-700">
              <Users className="h-5 w-5" />
            </div>
            {mode === 'join' && <Check className="h-4 w-4 text-[#23865B]" />}
          </div>
          <h3 className="text-sm font-bold text-[#18231E]">Join with Code</h3>
          <p className="mt-1 text-[11px] text-[#718078] leading-snug">
            Enter an invite code provided by your apartment association or neighbor.
          </p>
        </div>
      </div>

      {/* Form Card */}
      <Card className="p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'create' ? (
            <>
              <Input
                label="Apartment Society Name"
                value={societyName}
                onChange={(e) => setSocietyName(e.target.value)}
                placeholder="e.g. Greenfield Heights Residency"
                required
              />
              <Input
                label="Locality / Landmark & City"
                value={locality}
                onChange={(e) => setLocality(e.target.value)}
                placeholder="e.g. Kondapur, Hyderabad"
                required
              />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Input
                  label="Total Flats in Society (Optional)"
                  type="number"
                  value={totalFlats}
                  onChange={(e) => setTotalFlats(e.target.value)}
                  placeholder="e.g. 120"
                />
                <Input
                  label="Your Flat Number"
                  value={creatorFlat}
                  onChange={(e) => setCreatorFlat(e.target.value)}
                  placeholder="e.g. C-402"
                  required
                />
              </div>
              <Input
                label="Your Full Name"
                value={creatorName}
                onChange={(e) => setCreatorName(e.target.value)}
                placeholder="e.g. Rahul Sharma"
                required
              />
            </>
          ) : (
            <>
              <Input
                label="Society Invitation Code"
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value)}
                placeholder="e.g. GFH-2026"
                required
                hint="Sample valid invite code: GFH-2026"
                leftIcon={<KeyRound className="h-4 w-4" />}
              />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Input
                  label="Your Full Name"
                  value={joinName}
                  onChange={(e) => setJoinName(e.target.value)}
                  placeholder="e.g. Rahul Sharma"
                  required
                />
                <Input
                  label="Your Flat Number"
                  value={joinFlat}
                  onChange={(e) => setJoinFlat(e.target.value)}
                  placeholder="e.g. C-402"
                  required
                />
              </div>
            </>
          )}

          {error && <p className="text-xs text-[#D9534F] font-semibold">{error}</p>}

          <div className="pt-2">
            <Button type="submit" variant="primary" className="w-full">
              {mode === 'create' ? 'Create Community Workspace' : 'Join Society Group'}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
};
