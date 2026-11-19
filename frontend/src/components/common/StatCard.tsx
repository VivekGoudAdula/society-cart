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
 * Reusable StatCard for metrics across resident and volunteer dashboards.
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
    <Card hoverable={Boolean(onClick)} onClick={onClick} className={className}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-[#718078] tracking-tight">{label}</p>
          <h3 className="mt-1.5 text-2xl font-bold text-[#18231E] tracking-tight">{value}</h3>
          {subtext && <p className="mt-1 text-xs text-slate-500">{subtext}</p>}
          {trend && (
            <p
              className={`mt-1.5 text-[11px] font-semibold flex items-center gap-1 ${
                trend.isPositive ? 'text-emerald-600' : 'text-slate-500'
              }`}
            >
              <span>{trend.value}</span>
            </p>
          )}
        </div>
        {icon && (
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#EAF5EE] text-[#196B48]">
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
};
