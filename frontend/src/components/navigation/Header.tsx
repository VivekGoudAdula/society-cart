import React, { useState } from 'react';
import { Bell, Repeat, ShieldCheck, User, ChevronDown } from 'lucide-react';
import { useApp } from '../../context/AppContext';
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
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-[#EBE8DF] bg-white/95 backdrop-blur-xs px-4 sm:px-6">
      {/* Left: Greeting & Society Context */}
      <div className="flex items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold text-[#252824]">
              Good day, {currentUser.name.split(' ')[0]}
            </h2>
            <Badge
              size="sm"
              variant={currentRole === 'volunteer' ? 'primary' : currentRole === 'admin' ? 'warning' : 'neutral'}
            >
              {currentRole === 'volunteer' ? (
                <span className="flex items-center gap-1 font-semibold">
                  <ShieldCheck className="h-3 w-3 text-[#174D3A]" /> Volunteer
                </span>
              ) : currentRole === 'admin' ? (
                <span className="flex items-center gap-1 font-semibold">
                  <ShieldCheck className="h-3 w-3 text-amber-700" /> Admin
                </span>
              ) : (
                <span className="flex items-center gap-1 font-medium">
                  <User className="h-3 w-3 text-[#827F76]" /> Resident
                </span>
              )}
            </Badge>
          </div>

          {/* Society indicator with switcher dropdown if multiple societies */}
          <div className="relative inline-block text-[11px] text-[#827F76] hidden sm:block">
            {userSocieties.length > 1 ? (
              <button
                type="button"
                onClick={() => setShowSocietyMenu(!showSocietyMenu)}
                className="inline-flex items-center gap-1 font-semibold text-[#252824] hover:text-[#174D3A] transition-colors"
              >
                <span>{society?.name || 'Society Cart'}</span>
                <ChevronDown className="h-3 w-3" />
                <span className="text-[#827F76] font-normal">• Flat {currentUser.flatNumber}</span>
              </button>
            ) : (
              <span>
                {society?.name || 'Society Cart'} • Flat {currentUser.flatNumber}
              </span>
            )}

            {showSocietyMenu && userSocieties.length > 1 && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setShowSocietyMenu(false)} />
                <div className="absolute left-0 mt-1 w-56 rounded-2xl border border-[#EBE8DF] bg-white p-2 shadow-card z-50">
                  <p className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-[#827F76]">
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
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-xl text-xs font-semibold text-left transition-colors ${
                        pair.society.id === society?.id
                          ? 'bg-[#EBF2EE] text-[#174D3A]'
                          : 'text-[#252824] hover:bg-[#FAF9F6]'
                      }`}
                    >
                      <span className="truncate">{pair.society.name}</span>
                      <span className="text-[10px] text-[#827F76]">Flat {pair.membership.flat_number}</span>
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
          className="flex items-center gap-1.5 rounded-xl border border-[#DFDAD0] bg-[#FAF9F6] px-2.5 py-1.5 text-xs font-semibold text-[#252824] hover:bg-[#F3F0E8] transition-colors"
          title="Switch perspective"
        >
          <Repeat className="h-3.5 w-3.5 text-[#174D3A]" />
          <span className="hidden md:inline">
            Perspective: <strong className="capitalize text-[#174D3A]">{currentRole}</strong>
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
            className="relative rounded-xl border border-[#DFDAD0] p-2 text-[#827F76] hover:bg-[#FAF9F6] hover:text-[#252824] transition-colors"
            aria-label="View notifications"
          >
            <Bell className="h-4 w-4" />
            {unreadNotificationsCount > 0 && (
              <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-[#174D3A] text-[9px] font-bold text-white ring-2 ring-white">
                {unreadNotificationsCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowNotifications(false)} />
              <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl border border-[#EBE8DF] bg-white p-4 shadow-lifted z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                <div className="flex items-center justify-between pb-3 border-b border-[#EBE8DF]">
                  <h4 className="text-sm font-bold text-[#252824]">Notifications</h4>
                  <span className="text-[11px] text-[#827F76] font-medium">
                    {notifications.length} total
                  </span>
                </div>
                <div className="mt-2 max-h-72 overflow-y-auto space-y-2 divide-y divide-[#EBE8DF]/60">
                  {notifications.length === 0 ? (
                    <p className="py-6 text-center text-xs text-[#827F76]">No notifications yet</p>
                  ) : (
                    notifications.map((n) => (
                      <div key={n.id} className="pt-2.5 first:pt-0">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-xs font-bold text-[#252824]">{n.title}</p>
                          <span className="text-[10px] text-[#827F76] shrink-0">
                            {new Date(n.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                        <p className="text-xs text-[#827F76] mt-0.5 leading-relaxed">{n.description}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
};
