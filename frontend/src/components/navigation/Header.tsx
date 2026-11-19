import React, { useState } from 'react';
import { Bell, Repeat, ShieldCheck, User, ChevronDown } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Avatar } from '../common/Avatar';
import { Badge } from '../common/Badge';

/**
 * Top application header with notifications drawer, society badge, society switcher, and role indicator.
 */
export const Header: React.FC = () => {
  const {
    currentUser,
    currentRole,
    switchRole,
    society,
    userSocieties,
    setActiveSocietyId,
    notifications,
    unreadNotificationsCount,
    markNotificationsRead,
  } = useApp();

  const [showNotifications, setShowNotifications] = useState(false);
  const [showSocietyMenu, setShowSocietyMenu] = useState(false);

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-[#E6ECE8] bg-white/95 backdrop-blur-xs px-4 sm:px-6">
      {/* Left: Greeting & Society Context */}
      <div className="flex items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold text-[#18231E]">
              Good morning, {currentUser.name.split(' ')[0]} 👋
            </h2>
            <Badge
              size="sm"
              variant={currentRole === 'volunteer' ? 'primary' : currentRole === 'admin' ? 'warning' : 'neutral'}
            >
              {currentRole === 'volunteer' ? (
                <span className="flex items-center gap-1">
                  <ShieldCheck className="h-3 w-3 text-[#23865B]" /> Volunteer View
                </span>
              ) : currentRole === 'admin' ? (
                <span className="flex items-center gap-1">
                  <ShieldCheck className="h-3 w-3 text-amber-600" /> Admin View
                </span>
              ) : (
                <span className="flex items-center gap-1">
                  <User className="h-3 w-3 text-slate-500" /> Resident View
                </span>
              )}
            </Badge>
          </div>

          {/* Society indicator with switcher dropdown if multiple societies */}
          <div className="relative inline-block text-[11px] text-[#718078] hidden sm:block">
            {userSocieties.length > 1 ? (
              <button
                type="button"
                onClick={() => setShowSocietyMenu(!showSocietyMenu)}
                className="inline-flex items-center gap-1 font-semibold text-[#18231E] hover:text-[#23865B] transition-colors"
              >
                <span>{society.name}</span>
                <ChevronDown className="h-3 w-3" />
                <span className="text-[#718078] font-normal">• Flat {currentUser.flatNumber}</span>
              </button>
            ) : (
              <span>
                {society.name} • Flat {currentUser.flatNumber}
              </span>
            )}

            {showSocietyMenu && userSocieties.length > 1 && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setShowSocietyMenu(false)} />
                <div className="absolute left-0 mt-1 w-56 rounded-xl border border-[#E6ECE8] bg-white p-2 shadow-lg z-50">
                  <p className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Switch Society
                  </p>
                  {userSocieties.map((pair) => (
                    <button
                      key={pair.society.id}
                      type="button"
                      onClick={() => {
                        setActiveSocietyId(pair.society.id);
                        setShowSocietyMenu(false);
                      }}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-semibold text-left transition-colors ${
                        pair.society.id === society.id
                          ? 'bg-[#EAF5EE] text-[#196B48]'
                          : 'text-[#18231E] hover:bg-slate-50'
                      }`}
                    >
                      <span className="truncate">{pair.society.name}</span>
                      <span className="text-[10px] text-[#718078]">Flat {pair.membership.flat_number}</span>
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Right: Quick Role Toggle & Notifications */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Role Toggle Button */}
        <button
          onClick={() => switchRole(currentRole === 'resident' ? 'volunteer' : 'resident')}
          className="flex items-center gap-1.5 rounded-xl border border-[#E6ECE8] bg-slate-50 px-2.5 py-1.5 text-xs font-semibold text-[#18231E] hover:bg-slate-100 transition-colors"
          title="Switch role"
        >
          <Repeat className="h-3.5 w-3.5 text-[#23865B]" />
          <span className="hidden md:inline">
            Role: <strong className="capitalize">{currentRole}</strong>
          </span>
        </button>

        {/* Notifications Dropdown Container */}
        <div className="relative">
          <button
            onClick={() => {
              setShowNotifications(!showNotifications);
              if (!showNotifications && unreadNotificationsCount > 0) {
                markNotificationsRead();
              }
            }}
            className="relative rounded-xl border border-[#E6ECE8] p-2 text-slate-500 hover:bg-slate-50 hover:text-slate-700 transition-colors"
            aria-label="View notifications"
          >
            <Bell className="h-4 w-4" />
            {unreadNotificationsCount > 0 && (
              <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-[#23865B] text-[9px] font-bold text-white ring-2 ring-white">
                {unreadNotificationsCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setShowNotifications(false)}
              />
              <div className="absolute right-0 mt-2 w-80 rounded-2xl border border-[#E6ECE8] bg-white p-4 shadow-xl z-50">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <h4 className="text-xs font-bold text-[#18231E]">Notifications</h4>
                  <span className="text-[10px] text-[#718078]">Latest updates</span>
                </div>
                <div className="mt-2 divide-y divide-slate-50 max-h-72 overflow-y-auto">
                  {notifications.map((n) => (
                    <div key={n.id} className="py-2.5 text-left">
                      <p className="text-xs font-semibold text-[#18231E]">{n.title}</p>
                      <p className="mt-0.5 text-[11px] text-[#718078] leading-snug">{n.description}</p>
                      <span className="mt-1 block text-[10px] text-slate-400">{n.timestamp}</span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* User Avatar */}
        <Avatar
          name={currentUser.name}
          src={currentUser.avatarUrl}
          size="sm"
          roleTag={currentUser.role}
        />
      </div>
    </header>
  );
};
