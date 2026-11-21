import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

/**
 * Clean reusable Input component with accessible labels and error messages.
 */
export const Input: React.FC<InputProps> = ({
  label,
  error,
  hint,
  leftIcon,
  rightIcon,
  className = '',
  id,
  ...props
}) => {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={inputId} className="block text-xs font-semibold text-[#252824] mb-1.5 tracking-tight">
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        {leftIcon && (
          <div className="absolute left-3.5 flex items-center pointer-events-none text-[#827F76]">
            {leftIcon}
          </div>
        )}
        <input
          id={inputId}
          className={`w-full rounded-xl border bg-white px-3.5 py-2.5 text-sm text-[#252824] placeholder:text-[#827F76]/60 transition-all focus:outline-none focus:ring-2 focus:ring-[#174D3A]/20 disabled:bg-[#F3F0E8] disabled:text-[#827F76] ${
            leftIcon ? 'pl-10' : ''
          } ${rightIcon ? 'pr-10' : ''} ${
            error
              ? 'border-[#C0392B] focus:border-[#C0392B] focus:ring-[#C0392B]/20'
              : 'border-[#DFDAD0] focus:border-[#174D3A]'
          } ${className}`}
          {...props}
        />
        {rightIcon && (
          <div className="absolute right-3.5 flex items-center text-[#827F76]">
            {rightIcon}
          </div>
        )}
      </div>
      {error && <p className="mt-1.5 text-xs text-[#C0392B] font-medium">{error}</p>}
      {!error && hint && <p className="mt-1.5 text-xs text-[#827F76]">{hint}</p>}
    </div>
  );
};
