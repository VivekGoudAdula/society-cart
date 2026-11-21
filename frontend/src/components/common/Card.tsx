import React from 'react';

export interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  hoverable?: boolean;
}

/**
 * Reusable Card component adhering to Pinterest-inspired warm ivory & soft cream design tokens.
 */
export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  onClick,
  hoverable = false,
}) => {
  return (
    <div
      onClick={onClick}
      className={`rounded-2xl border border-[#EBE8DF] bg-white p-5 sm:p-6 shadow-soft transition-all duration-200 ${
        hoverable ? 'hover:border-[#DFDAD0] hover:shadow-card cursor-pointer' : ''
      } ${className}`}
    >
      {children}
    </div>
  );
};
