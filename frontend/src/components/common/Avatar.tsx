import React from 'react';

export interface AvatarProps {
  name: string;
  src?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  roleTag?: 'resident' | 'volunteer' | 'bot';
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

  const ringStyles = {
    volunteer: 'ring-2 ring-emerald-500',
    resident: 'ring-1 ring-slate-200',
    bot: 'ring-2 ring-indigo-400',
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
          className={`flex items-center justify-center rounded-full bg-[#EAF5EE] font-bold text-[#196B48] select-none ${
            sizeStyles[size]
          } ${roleTag ? ringStyles[roleTag] : ''} ${className}`}
        >
          {getInitials(name)}
        </div>
      )}
      {roleTag === 'volunteer' && (
        <span
          title="Society Volunteer"
          className="absolute -bottom-0.5 -right-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-emerald-600 text-[8px] font-bold text-white ring-1 ring-white"
        >
          V
        </span>
      )}
    </div>
  );
};
