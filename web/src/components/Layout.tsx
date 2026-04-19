import { NavLink } from 'react-router-dom'
import { Zap, TrendingUp, FileText, BookOpen, Microscope, Sliders } from 'lucide-react'
import type { ReactNode } from 'react'

const navItems = [
  { to: '/', icon: Zap, label: 'Active Signals', end: true },
  { to: '/performance', icon: TrendingUp, label: 'Performance', end: false },
  { to: '/trades', icon: FileText, label: 'Trade Log', end: false },
  { to: '/insights', icon: Microscope, label: 'Model Insights', end: false },
  { to: '/tuning', icon: Sliders, label: 'Tuning', end: false },
  { to: '/docs', icon: BookOpen, label: 'Docs', end: false },
]

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="flex h-screen bg-[#0d0d14] overflow-hidden">
      {/* Sidebar — desktop only */}
      <aside className="hidden md:flex flex-col w-60 shrink-0 bg-[#0a0a12] border-r border-[#1e1e3a]">
        {/* Branding */}
        <div className="flex items-center gap-2.5 px-5 py-5 border-b border-[#1e1e3a]">
          <div className="w-8 h-8 rounded-lg bg-[#9b6dff]/20 flex items-center justify-center">
            <Zap size={16} className="text-[#9b6dff]" />
          </div>
          <div>
            <div className="text-sm font-semibold text-[#e2e2f0] leading-tight">Football Intel</div>
            <div className="text-[10px] text-[#6b6b8a] uppercase tracking-widest">Betting Dashboard</div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                isActive
                  ? 'nav-link-active flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium'
                  : 'nav-link flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium'
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-[#1e1e3a]">
          <div className="text-[10px] text-[#6b6b8a] uppercase tracking-widest">Powered by Kalshi</div>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Top header — mobile shows branding, desktop shows page title area */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 bg-[#0a0a12] border-b border-[#1e1e3a]">
          <div className="w-7 h-7 rounded-lg bg-[#9b6dff]/20 flex items-center justify-center">
            <Zap size={14} className="text-[#9b6dff]" />
          </div>
          <div>
            <div className="text-sm font-semibold text-[#e2e2f0]">Football Intel</div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto pb-20 md:pb-0">
          {children}
        </main>
      </div>

      {/* Bottom tab bar — mobile only */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-[#0a0a12] border-t border-[#1e1e3a] flex z-50">
        {navItems.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center gap-1 py-3 text-[10px] font-medium transition-colors ${
                isActive ? 'text-[#9b6dff]' : 'text-[#6b6b8a]'
              }`
            }
          >
            <Icon size={18} />
            <span className="leading-none">{label.split(' ')[0]}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
