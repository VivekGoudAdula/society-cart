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
      className={`flex flex-col items-center justify-center p-8 text-center rounded-2xl border border-dashed border-[#E6ECE8] bg-white ${className}`}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#EAF5EE] text-[#196B48] mb-3">
        {icon}
      </div>
      <h4 className="text-base font-bold text-[#18231E]">{title}</h4>
      <p className="mt-1 max-w-sm text-xs text-[#718078] leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <Button size="sm" variant="primary" onClick={onAction} className="mt-4">
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
