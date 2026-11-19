import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import { ShoppingCart } from 'lucide-react';

/**
 * Centered layout for Welcome, Login, and Society Setup flows.
 */
export const AuthLayout: React.FC = () => {
  return (
    <div className="flex min-h-screen flex-col justify-between bg-[#F8FAF9] text-[#18231E]">
      {/* Top Navbar */}
      <header className="flex h-16 items-center justify-between px-6 border-b border-[#E6ECE8] bg-white">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#23865B] text-white shadow-xs">
            <ShoppingCart className="h-4 w-4" />
          </div>
          <span className="text-base font-bold text-[#18231E] tracking-tight">Society Cart</span>
        </Link>
        <span className="text-xs font-semibold text-[#23865B] bg-[#EAF5EE] px-2.5 py-1 rounded-full border border-[#23865B]/20">
          Nexconn Build Challenge 2026
        </span>
      </header>

      {/* Main Form Body */}
      <main className="flex flex-1 items-center justify-center p-4 sm:p-8">
        <div className="w-full max-w-xl">
          <Outlet />
        </div>
      </main>

      {/* Footer */}
      <footer className="py-4 text-center text-xs text-[#718078] border-t border-[#E6ECE8] bg-white">
        Society Cart — Community-Based Group Grocery Ordering • Hackathon Prototype
      </footer>
    </div>
  );
};
