import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  MessageSquare,
  ShoppingCart,
  Receipt,
  LogOut,
  Building2,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Avatar } from '../common/Avatar';
import { Badge } from '../common/Badge';

/**
 * Desktop left sidebar with Pinterest-inspired editorial lifestyle styling,
 * clear navigation groups, role-aware visibility, and tactile interactive elements.
 */
export const Sidebar: React.FC = () => {
  const { currentUser, currentRole, society, activeRound, logout } = useApp();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const isVolunteerOrAdmin = currentRole === 'volunteer' || currentRole === 'admin';

  return (
    <aside className="hidden lg:flex w-64 flex-col justify-between border-r border-[#EBE8DF] bg-white h-screen sticky top-0 px-4 py-5 select-none z-20">
      <div className="space-y-6">
        {/* Brand Header */}
        <div className="flex items-center gap-3 px-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#174D3A] text-white shadow-sm shadow-[#174D3A]/20">
            <ShoppingCart className="h-5 w-5" />
          </div>
          <div>
            <span className="text-base font-bold text-[#252824] tracking-tight block leading-tight">
              Society Cart
            </span>
            <span className="text-[10px] text-[#827F76] font-medium block">
              Community Bulk Order
            </span>
          </div>
        </div>

        {/* Current Society Card */}
        <div className="p-3.5 rounded-2xl bg-[#FAF9F6] border border-[#EBE8DF]">
          <div className="flex items-center gap-2 text-xs font-bold text-[#252824]">
            <Building2 className="h-4 w-4 text-[#174D3A] shrink-0" />
            <span className="truncate">{society?.name || 'Society Cart'}</span>
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px] text-[#827F76]">
            <span>Flat {currentUser?.flatNumber || '—'}</span>
            <Badge
              size="sm"
              variant={activeRound.status === 'open' ? 'primary' : 'neutral'}
              pulseDot={activeRound.status === 'open'}
            >
              Round #{activeRound.roundNumber} {activeRound.status.toUpperCase()}
            </Badge>
          </div>
        </div>

        {/* Navigation Groups */}
        <div className="space-y-5">
          {/* Group 1: General */}
          <div>
            <p className="px-3 text-[10px] font-bold uppercase tracking-wider text-[#827F76] mb-1.5">
              General
            </p>
            <nav className="space-y-1">
              <NavLink
                to={isVolunteerOrAdmin ? '/volunteer' : '/resident'}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs font-semibold transition-all ${
                    isActive
                      ? 'bg-[#EBF2EE] text-[#174D3A] font-bold'
                      : 'text-[#827F76] hover:bg-[#FAF9F6] hover:text-[#252824]'
                  }`
                }
              >
                <LayoutDashboard className="h-4 w-4 shrink-0" />
                <span>{isVolunteerOrAdmin ? 'Operations Overview' : 'Resident Overview'}</span>
              </NavLink>

              <NavLink
                to="/chat"
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs font-semibold transition-all ${
                    isActive
                      ? 'bg-[#EBF2EE] text-[#174D3A] font-bold'
                      : 'text-[#827F76] hover:bg-[#FAF9F6] hover:text-[#252824]'
                  }`
                }
              >
                <MessageSquare className="h-4 w-4 shrink-0" />
                <span>Society Chat</span>
              </NavLink>

              {!isVolunteerOrAdmin && (
                <NavLink
                  to="/order-summary"
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs font-semibold transition-all ${
                      isActive
                        ? 'bg-[#EBF2EE] text-[#174D3A] font-bold'
                        : 'text-[#827F76] hover:bg-[#FAF9F6] hover:text-[#252824]'
                    }`
                  }
                >
                  <Receipt className="h-4 w-4 shrink-0" />
                  <span>My Orders & Bills</span>
                </NavLink>
              )}
            </nav>
          </div>

          {/* Group 2: Management (Volunteers & Admins) */}
          {isVolunteerOrAdmin && (
            <div>
              <p className="px-3 text-[10px] font-bold uppercase tracking-wider text-[#827F76] mb-1.5">
                Procurement
              </p>
              <nav className="space-y-1">
                <NavLink
                  to="/shopping-list"
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs font-semibold transition-all ${
                      isActive
                        ? 'bg-[#EBF2EE] text-[#174D3A] font-bold'
                        : 'text-[#827F76] hover:bg-[#FAF9F6] hover:text-[#252824]'
                    }`
                  }
                >
                  <ShoppingCart className="h-4 w-4 shrink-0" />
                  <span>Bulk Shopping List</span>
                </NavLink>

                <NavLink
                  to="/order-summary"
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs font-semibold transition-all ${
                      isActive
                        ? 'bg-[#EBF2EE] text-[#174D3A] font-bold'
                        : 'text-[#827F76] hover:bg-[#FAF9F6] hover:text-[#252824]'
                    }`
                  }
                >
                  <Receipt className="h-4 w-4 shrink-0" />
                  <span>Billing & Savings</span>
                </NavLink>
              </nav>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Section: User Profile */}
      <div className="pt-4 border-t border-[#EBE8DF]">
        {/* User Card */}
        <div className="flex items-center justify-between px-1.5 pt-1">
          <div className="flex items-center gap-2.5 min-w-0">
            <Avatar name={currentUser.name} src={currentUser.avatarUrl} size="sm" roleTag={currentUser.role} />
            <div className="min-w-0">
              <p className="text-xs font-bold text-[#252824] truncate">{currentUser.name}</p>
              <p className="text-[11px] text-[#827F76] capitalize">
                {currentUser.role} • Flat {currentUser.flatNumber}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="p-1.5 text-[#827F76] hover:text-[#C0392B] rounded-lg hover:bg-[#FAF9F6] transition-colors"
            title="Sign Out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};
