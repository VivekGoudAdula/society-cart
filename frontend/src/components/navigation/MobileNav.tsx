import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, MessageSquare, ShoppingCart, Receipt } from 'lucide-react';
import { useApp } from '../../context/AppContext';

/**
 * Mobile bottom navigation bar for quick thumb-reach navigation on phones and tablets.
 */
export const MobileNav: React.FC = () => {
  const { currentRole } = useApp();

  const residentNavItems = [
    { label: 'Home', path: '/resident', icon: LayoutDashboard },
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
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 flex h-16 items-center justify-around border-t border-[#E6ECE8] bg-white/95 backdrop-blur-md px-3">
      {items.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          className={({ isActive }) =>
            `flex flex-col items-center justify-center py-1 px-3 text-[10px] font-semibold transition-all ${
              isActive ? 'text-[#23865B]' : 'text-[#718078] hover:text-[#18231E]'
            }`
          }
        >
          <item.icon className="h-5 w-5 mb-0.5" />
          <span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
};
