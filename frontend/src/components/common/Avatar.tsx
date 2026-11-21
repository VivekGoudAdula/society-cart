import React from 'react';

import { UserRole } from '../../types';

export interface AvatarProps {
  name: string;
  src?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  roleTag?: UserRole | 'bot';
  className?: string;
}

/**
 * Reusable Avatar with image fallback to clean initials and optional role ring.
 */
export const Avatar: React.FC<AvatarProps> = ({
  name,
  src,
  size = 'md',
  roleTag,
  className = '',
}) => {
  const getInitials = (text: string) => {
    return text
      .split(' ')
      .map((part) => part[0])
      .filter(Boolean)
      .slice(0, 2)
      .join('')
      .toUpperCase();
  };

  const sizeStyles = {
    sm: 'h-7 w-7 text-[11px]',
    md: 'h-9 w-9 text-xs',
    lg: 'h-11 w-11 text-sm',
    xl: 'h-14 w-14 text-base',
  };

  const ringStyles: Record<UserRole | 'bot', string> = {
    volunteer: 'ring-2 ring-[#174D3A]',
    resident: 'ring-1 ring-[#DFDAD0]',
    admin: 'ring-2 ring-amber-600',
    bot: 'ring-2 ring-emerald-600',
  };

  return (
    <div className="relative inline-flex shrink-0">
      {src ? (
        <img
          src={src}
          alt={name}
          className={`rounded-full object-cover ${sizeStyles[size]} ${
            roleTag ? ringStyles[roleTag] : ''
          } ${className}`}
        />
      ) : (
        <div
          className={`flex items-center justify-center rounded-full bg-[#EBF2EE] font-bold text-[#174D3A] border border-[#174D3A]/20 select-none ${
            sizeStyles[size]
          } ${roleTag ? ringStyles[roleTag] : ''} ${className}`}
        >
          {getInitials(name)}
        </div>
      )}
      {roleTag === 'volunteer' && (
        <span
          title="Society Volunteer"
          className="absolute -bottom-0.5 -right-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-[#174D3A] text-[8px] font-bold text-white ring-1 ring-white"
        >
          V
        </span>
      )}
    </div>
  );
};
