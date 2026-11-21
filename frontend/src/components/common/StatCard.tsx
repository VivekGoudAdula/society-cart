import React from 'react';
import { Card } from './Card';

export interface StatCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon?: React.ReactNode;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  onClick?: () => void;
  className?: string;
}

/**
 * Reusable StatCard for metrics across resident and volunteer dashboards in Pinterest-inspired styling.
 */
export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  subtext,
  icon,
  trend,
  onClick,
  className = '',
}) => {
  return (
    <Card hoverable={Boolean(onClick)} onClick={onClick} className={`bg-white border-[#EBE8DF] ${className}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold text-[#827F76] uppercase tracking-wider">{label}</p>
          <h3 className="mt-2 text-2xl sm:text-3xl font-extrabold text-[#252824] tracking-tight">{value}</h3>
          {subtext && <p className="mt-1 text-xs text-[#827F76]">{subtext}</p>}
          {trend && (
            <p
              className={`mt-2 text-[11px] font-semibold flex items-center gap-1 ${
                trend.isPositive ? 'text-[#174D3A]' : 'text-[#827F76]'
              }`}
            >
              <span>{trend.value}</span>
            </p>
          )}
        </div>
        {icon && (
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#EBF2EE] text-[#174D3A] shadow-xs">
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
};
