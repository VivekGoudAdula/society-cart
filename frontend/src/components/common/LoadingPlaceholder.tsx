import React from 'react';

export interface LoadingPlaceholderProps {
  className?: string;
  rows?: number;
}

/**
 * Skeleton placeholder for smooth loading visuals.
 */
export const LoadingPlaceholder: React.FC<LoadingPlaceholderProps> = ({
  className = '',
  rows = 3,
}) => {
  return (
    <div className={`space-y-3 animate-pulse ${className}`}>
      {Array.from({ length: rows }).map((_, idx) => (
        <div
          key={idx}
          className="h-4 bg-slate-200/70 rounded-md"
          style={{ width: `${100 - idx * 15}%` }}
        />
      ))}
    </div>
  );
};
