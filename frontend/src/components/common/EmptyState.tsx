import React from 'react';
import { Button } from './Button';

export interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

/**
 * Clean EmptyState illustration with optional CTA.
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 sm:p-12 text-center rounded-2xl border border-dashed border-[#DFDAD0] bg-white ${className}`}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#EBF2EE] text-[#174D3A] mb-3 shadow-xs">
        {icon}
      </div>
      <h4 className="text-base sm:text-lg font-bold text-[#252824] tracking-tight">{title}</h4>
      <p className="mt-1.5 max-w-sm text-xs sm:text-sm text-[#827F76] leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <Button size="sm" variant="primary" onClick={onAction} className="mt-5">
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
