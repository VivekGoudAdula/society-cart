import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

/**
 * Modern reusable Button component adhering to Society Cart design tokens.
 */
export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  className = '',
  disabled,
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded-xl transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed select-none active:scale-[0.98]';

  const sizeStyles = {
    sm: 'text-xs px-3 py-1.5 gap-1.5',
    md: 'text-sm px-4 py-2.5 gap-2',
    lg: 'text-base px-5 py-3 gap-2.5',
  };

  const variantStyles = {
    primary:
      'bg-[#23865B] text-white hover:bg-[#196B48] focus:ring-[#23865B]/40 shadow-sm shadow-[#23865B]/20',
    secondary:
      'bg-[#EAF5EE] text-[#196B48] hover:bg-[#d8ecdf] focus:ring-[#23865B]/30 font-semibold',
    outline:
      'border border-[#E6ECE8] bg-white text-[#18231E] hover:bg-slate-50 hover:border-slate-300 focus:ring-slate-200',
    ghost:
      'bg-transparent text-[#718078] hover:text-[#18231E] hover:bg-slate-100 focus:ring-slate-200',
    danger:
      'bg-[#D9534F] text-white hover:bg-[#c44340] focus:ring-[#D9534F]/30 shadow-sm shadow-[#D9534F]/20',
  };

  return (
    <button
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : (
        leftIcon
      )}
      <span>{children}</span>
      {!isLoading && rightIcon}
    </button>
  );
};
