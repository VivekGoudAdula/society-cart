import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, MessageSquare, ShoppingCart, Receipt } from 'lucide-react';
import { useApp } from '../../context/AppContext';

/**
 * Mobile bottom navigation bar with accessible touch targets (44px+)
 * and warm lifestyle palette styling.
 */
export const MobileNav: React.FC = () => {
  const { currentRole } = useApp();

  const residentNavItems = [
    { label: 'Overview', path: '/resident', icon: LayoutDashboard },
    { label: 'Chat', path: '/chat', icon: MessageSquare },
    { label: 'Orders', path: '/order-summary', icon: Receipt },
  ];

  const volunteerNavItems = [
    { label: 'Overview', path: '/volunteer', icon: LayoutDashboard },
    { label: 'Chat', path: '/chat', icon: MessageSquare },
    { label: 'Shop List', path: '/shopping-list', icon: ShoppingCart },
    { label: 'Bills', path: '/order-summary', icon: Receipt },
  ];

  const items = currentRole === 'resident' ? residentNavItems : volunteerNavItems;

  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 flex h-16 items-center justify-around border-t border-[#EBE8DF] bg-white/95 backdrop-blur-md px-3 shadow-soft">
      {items.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          className={({ isActive }) =>
            `flex flex-col items-center justify-center min-h-[44px] min-w-[56px] py-1 px-3 text-[11px] font-semibold transition-all ${
              isActive
                ? 'text-[#174D3A]'
                : 'text-[#827F76] hover:text-[#252824]'
            }`
          }
        >
          {({ isActive }) => (
            <>
              <div className={`p-1 rounded-xl transition-all ${isActive ? 'bg-[#EBF2EE]' : ''}`}>
                <item.icon className="h-5 w-5" />
              </div>
              <span className="mt-0.5">{item.label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
};
