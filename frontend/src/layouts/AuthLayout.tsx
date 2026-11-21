import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import { ShoppingCart } from 'lucide-react';

/**
 * Centered layout for Society Setup and onboarding flows with warm lifestyle aesthetics.
 */
export const AuthLayout: React.FC = () => {
  return (
    <div className="flex min-h-screen flex-col justify-between bg-[#FAF9F6] text-[#252824]">
      {/* Top Navbar */}
      <header className="flex h-16 items-center justify-between px-6 border-b border-[#EBE8DF] bg-white/90 backdrop-blur-xs">
        <Link to="/" className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#174D3A] text-white shadow-sm shadow-[#174D3A]/20">
            <ShoppingCart className="h-4 w-4" />
          </div>
          <span className="text-base font-bold text-[#252824] tracking-tight">Society Cart</span>
        </Link>
        <span className="text-xs font-semibold text-[#174D3A] bg-[#EBF2EE] px-3 py-1 rounded-full border border-[#174D3A]/15">
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
      <footer className="py-4 text-center text-xs text-[#827F76] border-t border-[#EBE8DF] bg-white">
        Society Cart — Community-Based Group Grocery Ordering • Built with Love for Apartment Communities
      </footer>
    </div>
  );
};
