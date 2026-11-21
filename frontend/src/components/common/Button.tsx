import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

/**
 * Modern reusable Button component adhering to Society Cart deep forest green & warm cream design tokens.
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
    'inline-flex items-center justify-center font-medium rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed select-none active:scale-[0.98]';

  const sizeStyles = {
    sm: 'text-xs px-3 py-1.5 gap-1.5',
    md: 'text-sm px-4 py-2.5 gap-2',
    lg: 'text-base px-6 py-3 gap-2.5 font-semibold',
  };

  const variantStyles = {
    primary:
      'bg-[#174D3A] text-white hover:bg-[#113A2B] focus:ring-[#174D3A]/30 shadow-sm shadow-[#174D3A]/20',
    secondary:
      'bg-[#F3F0E8] text-[#174D3A] hover:bg-[#EBE8DF] border border-[#DFDAD0] focus:ring-[#174D3A]/20 font-semibold',
    outline:
      'border border-[#DFDAD0] bg-white text-[#252824] hover:bg-[#FAF9F6] hover:border-[#A7B8A0] focus:ring-[#174D3A]/20',
    ghost:
      'bg-transparent text-[#827F76] hover:text-[#252824] hover:bg-[#F3F0E8]/70 focus:ring-[#DFDAD0]',
    danger:
      'bg-[#C0392B] text-white hover:bg-[#A93226] focus:ring-[#C0392B]/30 shadow-sm shadow-[#C0392B]/20',
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
