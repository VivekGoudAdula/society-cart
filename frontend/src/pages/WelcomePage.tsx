import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShoppingCart,
  ArrowRight,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  Users,
  MessageSquare,
  Package,
  Receipt,
  Scale,
  Lock,
  Menu,
  X,
  Eye,
  EyeOff,
  Building2,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { Modal } from '../components/common/Modal';

type AuthTab = 'login' | 'register';

/**
 * Public Landing Page: Premium Pinterest-inspired lifestyle product experience.
 * Features an editorial hero with `bg.png`, 3-step workflow, community benefits,
 * trust architecture, and an accessible authentication / demo portal.
 */
export const WelcomePage: React.FC = () => {
  const navigate = useNavigate();
  const { login, register, switchRole } = useApp();

  // Navigation mobile drawer
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Auth Modal State
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authTab, setAuthTab] = useState<AuthTab>('login');

  // Sign In State
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Register State
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regPassword, setRegPassword] = useState('');

  const [showPassword, setShowPassword] = useState(false);
  const [authError, setAuthError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleOpenAuth = (tab: AuthTab = 'login') => {
    setAuthTab(tab);
    setAuthError('');
    setAuthModalOpen(true);
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');

    if (!loginEmail.trim()) {
      setAuthError('Please enter your email address.');
      return;
    }
    if (!loginPassword.trim() || loginPassword.length < 6) {
      setAuthError('Password must be at least 6 characters.');
      return;
    }

    setIsLoading(true);
    const result = await login(loginEmail.trim(), loginPassword);
    setIsLoading(false);

    if (!result.success) {
      setAuthError(result.error || 'Invalid email or password.');
      return;
    }

    setAuthModalOpen(false);
    navigate('/resident');
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');

    if (!regName.trim()) {
      setAuthError('Please enter your full name.');
      return;
    }
    if (!regEmail.trim()) {
      setAuthError('Please enter your email address.');
      return;
    }
    if (!regPassword.trim() || regPassword.length < 6) {
      setAuthError('Password must be at least 6 characters.');
      return;
    }

    setIsLoading(true);
    const result = await register(
      regName.trim(),
      regEmail.trim(),
      regPassword,
      regPhone.trim() || undefined
    );
    setIsLoading(false);

    if (!result.success) {
      setAuthError(result.error || 'Registration failed.');
      return;
    }

    setAuthModalOpen(false);
    navigate('/society-setup');
  };

  const handleDemoAccess = (role: 'resident' | 'volunteer') => {
    switchRole(role);
    setAuthModalOpen(false);
    if (role === 'resident') {
      navigate('/resident');
    } else {
      navigate('/volunteer');
    }
  };

  return (
    <div className="min-h-screen bg-[#FAF9F6] text-[#252824] selection:bg-[#174D3A] selection:text-white flex flex-col justify-between">
      {/* ------------------------------------------------------------------- */}
      {/* 1. CLEAN EDITORIAL NAVBAR (MATCHING REFERENCE) */}
      {/* ------------------------------------------------------------------- */}
      <header className="sticky top-0 z-40 w-full bg-white/80 backdrop-blur-md border-b border-[#EBE8DF]/50 transition-all">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          {/* Left: Brand Identity */}
          <div className="flex items-center gap-2.5 cursor-pointer" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#174D3A] text-white shadow-xs">
              <ShoppingCart className="h-5 w-5" />
            </div>
            <span className="text-xl font-bold tracking-tight text-[#18181b]">
              Society Cart
            </span>
          </div>

          {/* Center Navigation Links (Desktop) */}
          <nav className="hidden md:flex items-center gap-9 text-sm font-medium text-[#4B5563]">
            <a href="#how-it-works" className="hover:text-[#18181b] transition-colors">
              How It Works
            </a>
            <a href="#community" className="hover:text-[#18181b] transition-colors">
              Residents
            </a>
            <a href="#community" className="hover:text-[#18181b] transition-colors">
              Volunteers
            </a>
          </nav>

          {/* Right Action CTAs */}
          <div className="hidden md:flex items-center gap-3">
            <button
              onClick={() => handleOpenAuth('login')}
              className="text-sm font-semibold text-[#4B5563] hover:text-[#18181b] px-4 py-2 rounded-full transition-colors"
            >
              Sign In
            </button>
            <button
              onClick={() => handleOpenAuth('register')}
              className="rounded-full bg-[#18181b] hover:bg-black text-white px-5 py-2.5 text-sm font-medium transition-all shadow-xs"
            >
              Create a Society
            </button>
          </div>

          {/* Mobile Hamburger Toggle */}
          <div className="flex md:hidden items-center gap-2">
            <button
              onClick={() => handleOpenAuth('login')}
              className="text-xs font-semibold text-[#18181b] px-3 py-1.5"
            >
              Sign In
            </button>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-[#252824] rounded-lg hover:bg-[#F3F0E8] transition-colors"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-b border-[#EBE8DF] bg-white px-4 py-5 space-y-4 shadow-sm">
            <nav className="flex flex-col space-y-3 text-sm font-semibold text-[#252824]">
              <a
                href="#how-it-works"
                onClick={() => setMobileMenuOpen(false)}
                className="py-1 text-[#4B5563] hover:text-[#18181b]"
              >
                How It Works
              </a>
              <a
                href="#community"
                onClick={() => setMobileMenuOpen(false)}
                className="py-1 text-[#4B5563] hover:text-[#18181b]"
              >
                Residents & Volunteers
              </a>
              <a
                href="#trust"
                onClick={() => setMobileMenuOpen(false)}
                className="py-1 text-[#4B5563] hover:text-[#18181b]"
              >
                Trust & Privacy
              </a>
            </nav>
            <div className="pt-3 border-t border-[#EBE8DF] flex flex-col gap-2.5">
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  handleOpenAuth('register');
                }}
                className="w-full rounded-full bg-[#18181b] hover:bg-black text-white py-2.5 text-sm font-semibold transition-all shadow-xs"
              >
                Create a Society
              </button>
            </div>
          </div>
        )}
      </header>

      {/* ------------------------------------------------------------------- */}
      {/* 2. HERO SECTION (16:9 PROPORTIONED, MATCHING USER REFERENCE IMAGE) */}
      {/* ------------------------------------------------------------------- */}
      <section className="relative overflow-hidden min-h-[calc(100vh-5rem)] flex flex-col justify-center py-8 sm:py-10">
        {/* Background sunset & apartment image: bg.png */}
        <div
          className="absolute inset-0 z-0 bg-cover bg-no-repeat pointer-events-none"
          style={{
            backgroundImage: "url('/bg.png')",
            backgroundPosition: 'center bottom',
          }}
        />
        {/* Top-to-bottom fade: pure white at top behind title/subhead, fading down so sunset clouds & apartments emerge */}
        <div className="absolute inset-0 z-0 bg-gradient-to-b from-white via-white/80 to-transparent pointer-events-none" />
        <div className="absolute inset-0 z-0 bg-gradient-to-t from-[#FAF9F6] via-transparent to-transparent pointer-events-none" />

        <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center my-auto">
          {/* Main Headline with Sans & Italic Serif Contrast */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-[#18181b] leading-[1.12] max-w-4xl mx-auto">
            Your Society. One Chat.
            <span className="font-serif italic font-normal text-[#18181b] block mt-1">
              One Bulk Order.
            </span>
          </h1>

          {/* Supporting Text */}
          <p className="mt-4 text-sm sm:text-base md:text-lg text-[#374151] max-w-2xl mx-auto font-normal leading-relaxed">
            Drop grocery needs in English, Telugu, or Hindi in your apartment group
            chat. AI structures every order so volunteers buy once in bulk.
          </p>

          {/* --------------------------------------------------------------- */}
          {/* 3 FLOATING INTERACTIVE HERO PREVIEWS (MATCHING REFERENCE IMAGE) */}
          {/* --------------------------------------------------------------- */}
          <div className="mt-8 sm:mt-12 flex flex-col md:flex-row items-center justify-center gap-4 sm:gap-5 max-w-4xl mx-auto">
            {/* Card 1: Resident Avatar / Ordering Groceries */}
            <div className="w-28 h-28 sm:w-32 sm:h-32 rounded-3xl bg-[#D6E6DE] border border-white/70 shadow-lg p-3 flex flex-col justify-end items-center relative overflow-hidden backdrop-blur-xs shrink-0">
              <div className="absolute inset-0 bg-gradient-to-t from-[#BCCFC5] to-[#E3EFE9]" />
              {/* Resident illustration with green shirt & laptop */}
              <div className="relative z-10 w-full flex flex-col items-center">
                {/* Person Head & Torso */}
                <div className="w-10 h-10 rounded-full bg-[#E5B594] border-2 border-[#D89B75] mb-1 relative overflow-hidden shadow-xs">
                  {/* Hair */}
                  <div className="absolute top-0 left-0 right-0 h-4 bg-[#2C211A] rounded-t-full" />
                </div>
                <div className="w-16 h-8 bg-[#3E7356] rounded-t-2xl flex items-center justify-center relative">
                  {/* Laptop */}
                  <div className="w-12 h-2.5 bg-slate-300 rounded-xs border-t border-white/80 shadow-xs translate-y-1" />
                </div>
              </div>
            </div>

            {/* Card 2: Society Group Chat Card (Centerpiece) */}
            <div className="w-full max-w-xs sm:w-80 rounded-3xl bg-white/75 backdrop-blur-md border border-white/80 p-4 shadow-xl text-left">
              {/* Header */}
              <div className="flex items-center justify-between pb-3 border-b border-black/5">
                <span className="text-xs font-bold text-[#18181b]">Society Group Chat</span>
                <span className="text-[10px] font-semibold text-[#8B5E14] bg-[#F7E7CD] px-2.5 py-0.5 rounded-full border border-[#ECD1A5]">
                  AI-parsed
                </span>
              </div>

              {/* Chat Message Bubble */}
              <div className="mt-3.5 space-y-1">
                <div className="flex items-center gap-1.5">
                  <div className="w-4 h-4 rounded-full bg-[#174D3A] text-white flex items-center justify-center text-[9px] font-bold">
                    R
                  </div>
                  <span className="text-[10px] font-semibold text-[#6B7280]">Resident</span>
                </div>
                <div className="rounded-2xl rounded-tl-sm bg-white/95 p-3 shadow-xs border border-white/90 text-xs font-medium text-[#18181b] leading-relaxed">
                  5 kg rice, 2L milk, 2 kg kandipappu kavali
                </div>
              </div>

              {/* Chat Input Bar */}
              <div className="mt-4 flex items-center gap-2 pt-2 border-t border-black/5">
                <div className="flex-1 text-[11px] text-[#9CA3AF] bg-white/70 rounded-full px-3 py-1.5 border border-white/60">
                  Type a message...
                </div>
                <div className="w-7 h-7 rounded-full bg-[#174D3A] text-white flex items-center justify-center shrink-0 shadow-xs cursor-pointer hover:bg-[#123C2D] transition-colors">
                  <ArrowRight className="h-3.5 w-3.5" />
                </div>
              </div>
            </div>

            {/* Card 3: Bulk Shopping List Card */}
            <div className="w-full max-w-xs sm:w-72 rounded-3xl bg-white/75 backdrop-blur-md border border-white/80 p-4 shadow-xl text-left">
              <div className="pb-3 border-b border-black/5">
                <span className="text-xs font-bold text-[#18181b]">Bulk Shopping List</span>
              </div>

              {/* 2x2 Category Grid */}
              <div className="mt-3 grid grid-cols-2 gap-2 text-[10px]">
                {/* Active category box (greenish) */}
                <div className="p-2.5 rounded-2xl bg-[#E8F1EC] border border-[#C5DED0] space-y-1">
                  <div className="flex items-center gap-1.5 font-bold text-[#174D3A]">
                    <CheckCircle2 className="h-3 w-3 text-[#174D3A]" />
                    <span>Rice (25 kg)</span>
                  </div>
                  <div className="flex items-center gap-1.5 font-semibold text-[#252824]">
                    <CheckCircle2 className="h-3 w-3 text-[#174D3A]" />
                    <span>Milk (12 L)</span>
                  </div>
                  <div className="flex items-center gap-1.5 font-semibold text-[#252824]">
                    <CheckCircle2 className="h-3 w-3 text-[#174D3A]" />
                    <span>Toor Dal (10 kg)</span>
                  </div>
                </div>

                {/* Secondary category box */}
                <div className="p-2.5 rounded-2xl bg-white/60 border border-white/80 space-y-1">
                  <div className="flex items-center gap-1.5 text-[#6B7280]">
                    <span className="w-2.5 h-2.5 rounded-xs border border-[#9CA3AF] inline-block" />
                    <span>Sunflower Oil</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[#6B7280]">
                    <span className="w-2.5 h-2.5 rounded-xs border border-[#9CA3AF] inline-block" />
                    <span>Sugar (15 kg)</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[#6B7280]">
                    <span className="w-2.5 h-2.5 rounded-xs border border-[#9CA3AF] inline-block" />
                    <span>Atta (40 kg)</span>
                  </div>
                </div>

                {/* Category box 3 */}
                <div className="p-2 rounded-xl bg-white/50 border border-white/70 space-y-0.5">
                  <div className="flex items-center gap-1 text-[#6B7280]">
                    <span className="w-2 h-2 rounded-xs border border-[#9CA3AF] inline-block" />
                    <span>Onions (30 kg)</span>
                  </div>
                  <div className="flex items-center gap-1 text-[#6B7280]">
                    <span className="w-2 h-2 rounded-xs border border-[#9CA3AF] inline-block" />
                    <span>Potatoes</span>
                  </div>
                </div>

                {/* Category box 4 */}
                <div className="p-2 rounded-xl bg-white/50 border border-white/70 space-y-0.5">
                  <div className="flex items-center gap-1 text-[#6B7280]">
                    <span className="w-2 h-2 rounded-xs border border-[#9CA3AF] inline-block" />
                    <span>Paneer & Butter</span>
                  </div>
                  <div className="flex items-center gap-1 text-[#6B7280]">
                    <span className="w-2 h-2 rounded-xs border border-[#9CA3AF] inline-block" />
                    <span>Detergent</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* 3. SECTION 1 — HOW IT WORKS */}
      {/* ------------------------------------------------------------------- */}
      <section id="how-it-works" className="py-20 sm:py-28 bg-[#F3F0E8]/50 border-y border-[#EBE8DF]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <span className="text-xs font-bold tracking-widest uppercase text-[#174D3A] bg-[#EBF2EE] px-3.5 py-1 rounded-full border border-[#174D3A]/15">
              Effortless Workflow
            </span>
            <h2 className="mt-4 text-3xl sm:text-4xl font-extrabold text-[#252824] tracking-tight">
              How Society Cart Works
            </h2>
            <p className="mt-3 text-base text-[#827F76]">
              Three simple steps turn chaotic chat messages into organized bulk savings for your entire apartment.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Step 1 */}
            <div className="rounded-3xl bg-white border border-[#EBE8DF] p-8 shadow-soft flex flex-col justify-between hover:shadow-card transition-all">
              <div>
                <div className="flex items-center justify-between mb-6">
                  <span className="font-serif italic text-3xl font-normal text-[#174D3A]">01</span>
                  <div className="h-12 w-12 rounded-2xl bg-[#EBF2EE] text-[#174D3A] flex items-center justify-center">
                    <MessageSquare className="h-6 w-6" />
                  </div>
                </div>
                <h3 className="text-xl font-bold text-[#252824] tracking-tight mb-2">
                  Residents Drop Their Needs
                </h3>
                <p className="text-sm text-[#827F76] leading-relaxed">
                  Residents send ordinary grocery requests in English, Telugu, or Hindi through the society chat.
                  No complex checkout forms or rigid app screens.
                </p>
              </div>
              <div className="mt-6 pt-4 border-t border-[#EBE8DF] text-xs font-semibold text-[#174D3A] flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4" />
                <span>Multilingual & Natural Language</span>
              </div>
            </div>

            {/* Step 2 */}
            <div className="rounded-3xl bg-white border border-[#EBE8DF] p-8 shadow-soft flex flex-col justify-between hover:shadow-card transition-all">
              <div>
                <div className="flex items-center justify-between mb-6">
                  <span className="font-serif italic text-3xl font-normal text-[#174D3A]">02</span>
                  <div className="h-12 w-12 rounded-2xl bg-[#EBF2EE] text-[#174D3A] flex items-center justify-center">
                    <Sparkles className="h-6 w-6" />
                  </div>
                </div>
                <h3 className="text-xl font-bold text-[#252824] tracking-tight mb-2">
                  AI Organizes Everything
                </h3>
                <p className="text-sm text-[#827F76] leading-relaxed">
                  Society Cart’s Groq parser identifies items, brands, and quantities, resolving ambiguities
                  and assembling one clean consolidated shopping list across all flats.
                </p>
              </div>
              <div className="mt-6 pt-4 border-t border-[#EBE8DF] text-xs font-semibold text-[#174D3A] flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4" />
                <span>Unit Normalization & Grouping</span>
              </div>
            </div>

            {/* Step 3 */}
            <div className="rounded-3xl bg-white border border-[#EBE8DF] p-8 shadow-soft flex flex-col justify-between hover:shadow-card transition-all">
              <div>
                <div className="flex items-center justify-between mb-6">
                  <span className="font-serif italic text-3xl font-normal text-[#174D3A]">03</span>
                  <div className="h-12 w-12 rounded-2xl bg-[#EBF2EE] text-[#174D3A] flex items-center justify-center">
                    <Package className="h-6 w-6" />
                  </div>
                </div>
                <h3 className="text-xl font-bold text-[#252824] tracking-tight mb-2">
                  Volunteers Shop Together
                </h3>
                <p className="text-sm text-[#827F76] leading-relaxed">
                  Volunteers buy wholesale, allocate quantities by flat, and generate individual itemized bills.
                  Discounts are passed directly to each household.
                </p>
              </div>
              <div className="mt-6 pt-4 border-t border-[#EBE8DF] text-xs font-semibold text-[#174D3A] flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4" />
                <span>Flat-Wise Packing & Private Bills</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* 4. SECTION 2 — DESIGNED FOR YOUR COMMUNITY */}
      {/* ------------------------------------------------------------------- */}
      <section id="community" className="py-20 sm:py-28 bg-[#FAF9F6]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <span className="text-xs font-bold tracking-widest uppercase text-[#174D3A] bg-[#EBF2EE] px-3.5 py-1 rounded-full border border-[#174D3A]/15">
              Community Roles
            </span>
            <h2 className="mt-4 text-3xl sm:text-4xl font-extrabold text-[#252824] tracking-tight">
              Designed for Your Community
            </h2>
            <p className="mt-3 text-base text-[#827F76]">
              A balanced experience created specifically for both apartment residents and community volunteers.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 sm:gap-12">
            {/* Resident Experience Card */}
            <div className="rounded-3xl bg-white border border-[#EBE8DF] p-8 sm:p-10 shadow-soft">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#EBF2EE] text-[#174D3A] text-xs font-bold mb-6">
                <Users className="h-3.5 w-3.5" /> For Residents
              </div>
              <h3 className="text-2xl font-bold text-[#252824] tracking-tight">
                Effortless grocery ordering right from group chat.
              </h3>
              <p className="mt-3 text-sm text-[#827F76] leading-relaxed">
                Enjoy wholesale market savings without driving to wholesale mandis or coordinating messy spreadsheets.
              </p>

              <div className="mt-8 space-y-4">
                {[
                  {
                    title: 'Easy Grocery Requests',
                    desc: 'Type your list in English, Telugu, Hindi, or conversational shorthand.',
                  },
                  {
                    title: 'Multilingual AI Understanding',
                    desc: 'AI interprets colloquial words, brands, and ambiguous quantities automatically.',
                  },
                  {
                    title: 'One-Tap Order Confirmation',
                    desc: 'Review, edit, and confirm extracted items before orders enter the pool.',
                  },
                  {
                    title: 'Private Individual Bills',
                    desc: 'Your flat’s items and costs remain completely private to your household.',
                  },
                  {
                    title: 'Transparent Verified Savings',
                    desc: 'Compare actual bulk savings against quick-commerce retail benchmarks.',
                  },
                ].map((item, idx) => (
                  <div key={idx} className="flex items-start gap-3">
                    <div className="h-5 w-5 rounded-full bg-[#EBF2EE] text-[#174D3A] flex items-center justify-center shrink-0 mt-0.5">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-[#252824]">{item.title}</h4>
                      <p className="text-xs text-[#827F76] mt-0.5">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Volunteer Experience Card */}
            <div className="rounded-3xl bg-[#F8F6F0] border border-[#DFDAD0] p-8 sm:p-10 shadow-soft">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#174D3A] text-white text-xs font-bold mb-6">
                <ShieldCheck className="h-3.5 w-3.5" /> For Volunteers
              </div>
              <h3 className="text-2xl font-bold text-[#252824] tracking-tight">
                A streamlined operational hub for bulk procurement.
              </h3>
              <p className="mt-3 text-sm text-[#827F76] leading-relaxed">
                Compile lists with one click, record actual store purchase receipts, and eliminate distribution headaches.
              </p>

              <div className="mt-8 space-y-4">
                {[
                  {
                    title: 'Manage Order Rounds',
                    desc: 'Schedule shopping drives with automatic deadline enforcement and closure.',
                  },
                  {
                    title: 'Consolidated Category Lists',
                    desc: 'Aggregate identical items across 10 canonical grocery categories with unit conversion.',
                  },
                  {
                    title: 'Actual Purchase Recording',
                    desc: 'Record real shop receipts, wholesale bulk prices, and brand substitutions.',
                  },
                  {
                    title: 'Flat-Wise Packing Breakdown',
                    desc: 'Pack individual resident bags using interactive checkboxes by flat number.',
                  },
                  {
                    title: 'Automated Fair Billing',
                    desc: 'Distribute wholesale costs and shared tempo expenses down to the exact paise.',
                  },
                ].map((item, idx) => (
                  <div key={idx} className="flex items-start gap-3">
                    <div className="h-5 w-5 rounded-full bg-[#174D3A] text-white flex items-center justify-center shrink-0 mt-0.5">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-[#252824]">{item.title}</h4>
                      <p className="text-xs text-[#827F76] mt-0.5">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* 5. SECTION 3 — BUILT AROUND TRUST */}
      {/* ------------------------------------------------------------------- */}
      <section id="trust" className="py-20 sm:py-28 bg-[#FAF9F6] border-t border-[#EBE8DF]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <span className="text-xs font-bold tracking-widest uppercase text-[#174D3A] bg-[#EBF2EE] px-3.5 py-1 rounded-full border border-[#174D3A]/15">
              Privacy & Accuracy
            </span>
            <h2 className="mt-4 text-3xl sm:text-4xl font-extrabold text-[#252824] tracking-tight">
              Built Around Trust
            </h2>
            <p className="mt-3 text-base text-[#827F76]">
              Every architectural decision is built to protect resident privacy, ensure fairness, and eliminate confusion.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Trust Pillar 1 */}
            <div className="rounded-2xl bg-white border border-[#EBE8DF] p-6 shadow-soft">
              <div className="h-10 w-10 rounded-xl bg-[#EBF2EE] text-[#174D3A] flex items-center justify-center mb-4">
                <Lock className="h-5 w-5" />
              </div>
              <h3 className="text-base font-bold text-[#252824]">Private Resident Bills</h3>
              <p className="mt-2 text-xs text-[#827F76] leading-relaxed">
                Individual flat purchases and bills are never broadcasted into public group chats. Only authorized flat members can view their invoices.
              </p>
            </div>

            {/* Trust Pillar 2 */}
            <div className="rounded-2xl bg-white border border-[#EBE8DF] p-6 shadow-soft">
              <div className="h-10 w-10 rounded-xl bg-[#EBF2EE] text-[#174D3A] flex items-center justify-center mb-4">
                <Building2 className="h-5 w-5" />
              </div>
              <h3 className="text-base font-bold text-[#252824]">Society-Level Access</h3>
              <p className="mt-2 text-xs text-[#827F76] leading-relaxed">
                Data is strictly segregated by apartment society with verified invite codes and role-based permissions preventing unauthorized access.
              </p>
            </div>

            {/* Trust Pillar 3 */}
            <div className="rounded-2xl bg-white border border-[#EBE8DF] p-6 shadow-soft">
              <div className="h-10 w-10 rounded-xl bg-[#EBF2EE] text-[#174D3A] flex items-center justify-center mb-4">
                <Scale className="h-5 w-5" />
              </div>
              <h3 className="text-base font-bold text-[#252824]">Verified Benchmarks</h3>
              <p className="mt-2 text-xs text-[#827F76] leading-relaxed">
                Savings are calculated against verified real retail prices (e.g. Zepto, Blinkit). We report honest figures without fake claims.
              </p>
            </div>

            {/* Trust Pillar 4 */}
            <div className="rounded-2xl bg-white border border-[#EBE8DF] p-6 shadow-soft">
              <div className="h-10 w-10 rounded-xl bg-[#EBF2EE] text-[#174D3A] flex items-center justify-center mb-4">
                <Receipt className="h-5 w-5" />
              </div>
              <h3 className="text-base font-bold text-[#252824]">Exact Cost Allocation</h3>
              <p className="mt-2 text-xs text-[#827F76] leading-relaxed">
                Decimal-safe financial arithmetic ensures every rupee matches actual receipts. Residents are never billed for items they didn't receive.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* 6. SECTION 4 — FINAL CTA */}
      {/* ------------------------------------------------------------------- */}
      <section className="py-20 sm:py-24 bg-[#FAF9F6]">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="rounded-3xl bg-[#174D3A] text-white p-8 sm:p-14 text-center shadow-lifted relative overflow-hidden">
            <div className="relative z-10 max-w-2xl mx-auto">
              <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight leading-tight">
                Better shopping starts with your community.
              </h2>
              <p className="mt-4 text-sm sm:text-base text-white/80 leading-relaxed">
                Join forward-thinking apartment societies coordinating bulk grocery buying today.
                Simple to set up, effortless to use.
              </p>
              <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
                <button
                  onClick={() => handleOpenAuth('register')}
                  className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-white text-[#174D3A] font-bold text-sm hover:bg-[#F3F0E8] transition-all shadow-sm active:scale-[0.98]"
                >
                  Create Your Society
                </button>
                <button
                  onClick={() => handleOpenAuth('login')}
                  className="w-full sm:w-auto px-8 py-3.5 rounded-xl border border-white/30 text-white font-semibold text-sm hover:bg-white/10 transition-all"
                >
                  Sign In
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* 7. FOOTER */}
      {/* ------------------------------------------------------------------- */}
      <footer className="border-t border-[#EBE8DF] bg-white py-12 text-[#827F76] text-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#174D3A] text-white">
              <ShoppingCart className="h-4 w-4" />
            </div>
            <span className="text-sm font-bold text-[#252824]">Society Cart</span>
            <span className="text-slate-300">|</span>
            <span>Nexconn Build Challenge 2026</span>
          </div>

          <div className="flex items-center gap-6 font-medium">
            <a href="#how-it-works" className="hover:text-[#174D3A] transition-colors">
              How It Works
            </a>
            <a href="#community" className="hover:text-[#174D3A] transition-colors">
              Community
            </a>
            <a href="#trust" className="hover:text-[#174D3A] transition-colors">
              Trust & Privacy
            </a>
            <button
              onClick={() => handleDemoAccess('resident')}
              className="hover:text-[#174D3A] transition-colors font-semibold text-[#174D3A]"
            >
              Demo Portal
            </button>
          </div>

          <div>
            © {new Date().getFullYear()} Society Cart. All rights reserved.
          </div>
        </div>
      </footer>

      {/* ------------------------------------------------------------------- */}
      {/* 8. AUTHENTICATION & DEMO MODAL */}
      {/* ------------------------------------------------------------------- */}
      <Modal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        title={authTab === 'login' ? 'Sign in to Society Cart' : 'Create Your Account'}
        description={
          authTab === 'login'
            ? 'Access your apartment society bulk orders, chat, and bills.'
            : 'Get started and join or create a grocery buying group for your flat.'
        }
        maxWidth="md"
      >
        <div className="space-y-5">
          {/* Tabs */}
          <div className="flex rounded-xl bg-[#F3F0E8] p-1">
            <button
              type="button"
              onClick={() => {
                setAuthTab('login');
                setAuthError('');
              }}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                authTab === 'login'
                  ? 'bg-white text-[#174D3A] shadow-xs'
                  : 'text-[#827F76] hover:text-[#252824]'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setAuthTab('register');
                setAuthError('');
              }}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                authTab === 'register'
                  ? 'bg-white text-[#174D3A] shadow-xs'
                  : 'text-[#827F76] hover:text-[#252824]'
              }`}
            >
              Register
            </button>
          </div>

          {authError && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-xs font-semibold text-rose-800">
              {authError}
            </div>
          )}

          {/* Form */}
          {authTab === 'login' ? (
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <Input
                label="Email Address"
                type="email"
                placeholder="you@society.com"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                required
              />
              <div className="space-y-1">
                <Input
                  label="Password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  required
                  rightIcon={
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="text-[#827F76] hover:text-[#252824]"
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  }
                />
              </div>
              <Button type="submit" variant="primary" size="md" className="w-full mt-2" isLoading={isLoading}>
                Sign In
              </Button>
            </form>
          ) : (
            <form onSubmit={handleRegisterSubmit} className="space-y-3.5">
              <Input
                label="Full Name"
                placeholder="Vivek Sharma"
                value={regName}
                onChange={(e) => setRegName(e.target.value)}
                required
              />
              <Input
                label="Email Address"
                type="email"
                placeholder="you@society.com"
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
                required
              />
              <Input
                label="Phone Number (Optional)"
                type="tel"
                placeholder="+91 98765 43210"
                value={regPhone}
                onChange={(e) => setRegPhone(e.target.value)}
              />
              <Input
                label="Password"
                type={showPassword ? 'text' : 'password'}
                placeholder="At least 6 characters"
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
                required
                rightIcon={
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="text-[#827F76] hover:text-[#252824]"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                }
              />
              <Button type="submit" variant="primary" size="md" className="w-full mt-2" isLoading={isLoading}>
                Create Account
              </Button>
            </form>
          )}

          {/* Reviewer Quick Access Portals */}
          <div className="pt-4 border-t border-[#EBE8DF]">
            <p className="text-[11px] font-bold text-[#827F76] uppercase tracking-wider mb-2.5 text-center">
              Quick Reviewer Portals (1-Click Evaluation)
            </p>
            <div className="grid grid-cols-2 gap-2.5">
              <button
                type="button"
                onClick={() => handleDemoAccess('resident')}
                className="p-2.5 rounded-xl border border-[#DFDAD0] bg-[#FAF9F6] hover:bg-[#F3F0E8] hover:border-[#174D3A]/30 text-left transition-all"
              >
                <div className="text-xs font-bold text-[#252824]">Resident Portal</div>
                <div className="text-[10px] text-[#827F76]">Chat, review & bills</div>
              </button>
              <button
                type="button"
                onClick={() => handleDemoAccess('volunteer')}
                className="p-2.5 rounded-xl border border-[#DFDAD0] bg-[#FAF9F6] hover:bg-[#F3F0E8] hover:border-[#174D3A]/30 text-left transition-all"
              >
                <div className="text-xs font-bold text-[#252824]">Volunteer Hub</div>
                <div className="text-[10px] text-[#827F76]">Rounds, packing & costs</div>
              </button>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
};
