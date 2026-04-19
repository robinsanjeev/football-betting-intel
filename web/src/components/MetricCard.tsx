import type { ReactNode } from 'react'

interface MetricCardProps {
  label: string
  value: string | number
  subValue?: string
  icon?: ReactNode
  trend?: 'positive' | 'negative' | 'neutral'
  valueColor?: string
  className?: string
}

export default function MetricCard({
  label,
  value,
  subValue,
  icon,
  trend = 'neutral',
  valueColor,
  className = '',
}: MetricCardProps) {
  const defaultColor =
    trend === 'positive'
      ? 'text-[#3ddc84]'
      : trend === 'negative'
      ? 'text-[#e84040]'
      : 'text-[#e2e2f0]'

  const color = valueColor ?? defaultColor

  return (
    <div className={`card p-4 flex flex-col gap-2 ${className}`}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-widest text-[#6b6b8a] font-medium">
          {label}
        </span>
        {icon && (
          <span className="text-[#6b6b8a]">{icon}</span>
        )}
      </div>
      <div className="flex flex-col gap-0.5">
        <span className={`font-mono text-2xl font-semibold tracking-tight ${color}`}>
          {value}
        </span>
        {subValue && (
          <span className="text-xs text-[#6b6b8a]">{subValue}</span>
        )}
      </div>
    </div>
  )
}
