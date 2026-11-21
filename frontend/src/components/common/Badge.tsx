import React from 'react';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'neutral' | 'sage';
  size?: 'sm' | 'md';
  pulseDot?: boolean;
  className?: string;
}

/**
 * Reusable Badge for statuses, categories, and tags in Pinterest-inspired palette.
 */
export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  pulseDot = false,
  className = '',
}) => {
  const variantStyles = {
    primary: 'bg-[#EBF2EE] text-[#174D3A] border border-[#174D3A]/15 font-semibold',
    success: 'bg-emerald-50 text-emerald-800 border border-emerald-200/80',
    warning: 'bg-amber-50 text-amber-800 border border-amber-200/80',
    danger: 'bg-rose-50 text-rose-800 border border-rose-200/80',
    neutral: 'bg-[#F3F0E8] text-[#252824] border border-[#DFDAD0]',
    sage: 'bg-[#A7B8A0]/15 text-[#174D3A] border border-[#A7B8A0]/30 font-medium',
  };

  const dotStyles = {
    primary: 'bg-[#174D3A]',
    success: 'bg-emerald-600',
    warning: 'bg-amber-600',
    danger: 'bg-rose-600',
    neutral: 'bg-[#827F76]',
    sage: 'bg-[#174D3A]',
  };

  const sizeStyles = {
    sm: 'text-[11px] px-2 py-0.5 gap-1 font-medium',
    md: 'text-xs px-2.5 py-1 gap-1.5 font-semibold',
  };

  return (
    <span
      className={`inline-flex items-center rounded-full ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
    >
      {pulseDot && (
        <span className="relative flex h-2 w-2">
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${dotStyles[variant]}`}
          />
          <span className={`relative inline-flex rounded-full h-2 w-2 ${dotStyles[variant]}`} />
        </span>
      )}
      {children}
    </span>
  );
};
