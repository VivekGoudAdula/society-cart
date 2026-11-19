import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  MessageSquare,
  ShoppingCart,
  Receipt,
  Repeat,
  LogOut,
  Building2,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Avatar } from '../common/Avatar';
import { Badge } from '../common/Badge';

/**
 * Desktop left sidebar with role-aware navigation and demo role switcher.
 */
export const Sidebar: React.FC = () => {
  const { currentUser, currentRole, switchRole, society, activeRound } = useApp();
  const navigate = useNavigate();

  const handleRoleToggle = () => {
    if (currentRole === 'resident') {
      switchRole('volunteer');
      navigate('/volunteer');
    } else {
      switchRole('resident');
      navigate('/resident');
    }
  };

  const residentNavItems = [
    { label: 'Dashboard', path: '/resident', icon: LayoutDashboard },
    { label: 'Society Chat', path: '/chat', icon: MessageSquare },
    { label: 'My Orders & Bills', path: '/order-summary', icon: Receipt },
  ];

  const volunteerNavItems = [
    { label: 'Operations Dashboard', path: '/volunteer', icon: LayoutDashboard },
    { label: 'Society Chat', path: '/chat', icon: MessageSquare },
    { label: 'Bulk Shopping List', path: '/shopping-list', icon: ShoppingCart },
    { label: 'Orders & Savings', path: '/order-summary', icon: Receipt },
  ];

  const navItems = currentRole === 'resident' ? residentNavItems : volunteerNavItems;

  return (
    <aside className="hidden lg:flex w-64 flex-col justify-between border-r border-[#E6ECE8] bg-white h-screen sticky top-0 px-4 py-5 select-none z-20">
      <div>
        {/* Brand */}
        <div className="flex items-center gap-3 px-2 mb-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#23865B] text-white shadow-sm shadow-[#23865B]/20">
            <ShoppingCart className="h-5 w-5" />
          </div>
          <div>
            <span className="text-base font-bold text-[#18231E] tracking-tight block">Society Cart</span>
            <span className="text-[10px] text-[#718078] font-medium block">One Chat. One Bulk Order.</span>
          </div>
        </div>

        {/* Current Society Card */}
        <div className="mx-1 mb-5 p-3 rounded-xl bg-[#F8FAF9] border border-[#E6ECE8]">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#18231E]">
            <Building2 className="h-4 w-4 text-[#23865B]" />
            <span className="truncate">{society.name}</span>
          </div>
          <div className="mt-1 flex items-center justify-between text-[11px] text-[#718078]">
            <span>Flat {currentUser.flatNumber}</span>
            <Badge size="sm" variant={activeRound.status === 'open' ? 'success' : 'neutral'} pulseDot={activeRound.status === 'open'}>
              Round #{activeRound.roundNumber} {activeRound.status.toUpperCase()}
            </Badge>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="space-y-1">
          <p className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">
            Menu ({currentRole})
          </p>
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-[#EAF5EE] text-[#196B48]'
                    : 'text-[#718078] hover:bg-slate-50 hover:text-[#18231E]'
                }`
              }
            >
              <item.icon className="h-4 w-4 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Bottom Section: Role Switcher & User Profile */}
      <div className="pt-4 border-t border-[#E6ECE8] space-y-3">
        {/* Role Switcher Pill */}
        <button
          onClick={handleRoleToggle}
          className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold border border-dashed border-[#23865B]/40 bg-[#EAF5EE]/60 text-[#196B48] hover:bg-[#EAF5EE] transition-colors"
          title="Click to toggle perspective"
        >
          <div className="flex items-center gap-2">
            <Repeat className="h-3.5 w-3.5" />
            <span>Switch to {currentRole === 'resident' ? 'Volunteer' : 'Resident'}</span>
          </div>
          <span className="text-[10px] bg-[#23865B] text-white px-1.5 py-0.5 rounded-md font-bold uppercase">
            DEMO
          </span>
        </button>

        {/* User Card */}
        <div className="flex items-center justify-between px-2 pt-1">
          <div className="flex items-center gap-2.5 min-w-0">
            <Avatar name={currentUser.name} src={currentUser.avatarUrl} size="sm" roleTag={currentUser.role} />
            <div className="min-w-0">
              <p className="text-xs font-bold text-[#18231E] truncate">{currentUser.name}</p>
              <p className="text-[11px] text-[#718078] capitalize">{currentUser.role} • Flat {currentUser.flatNumber}</p>
            </div>
          </div>
          <button
            onClick={() => navigate('/')}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
            title="Sign Out / Back to Welcome"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};
