import { useState } from 'react'
import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  Cpu,
  FileText,
  HelpCircle,
  Lightbulb,
  Microscope,
  Rocket,
  Server,
  Settings,
  Target,
  TrendingUp,
  Trophy,
  Wrench,
  Zap,
} from 'lucide-react'

// ─── Shared sub-components ───────────────────────────────────────────────────

function SectionAnchor({ id }: { id: string }) {
  return <span id={id} className="relative -top-20 block h-0 overflow-hidden" />
}

function CodeBlock({ children }: { children: React.ReactNode }) {
  return (
    <pre className="mt-2 p-3 rounded-lg bg-[#050510] border border-[#1e1e3a] text-[11px] font-mono text-[#9b6dff] leading-relaxed overflow-x-auto whitespace-pre-wrap break-all">
      {children}
    </pre>
  )
}

function InlineCode({ children }: { children: React.ReactNode }) {
  return (
    <code className="px-1.5 py-0.5 rounded bg-[#0f0f1e] border border-[#1e1e3a] text-[11px] font-mono text-[#c0b0e0]">
      {children}
    </code>
  )
}

function Note({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-3 px-3 py-2.5 rounded-lg bg-[#9b6dff]/5 border border-[#9b6dff]/20 text-[11px] text-[#c0b0e0] leading-relaxed flex gap-2">
      <Lightbulb size={12} className="text-[#9b6dff] shrink-0 mt-0.5" />
      <div>{children}</div>
    </div>
  )
}

function SectionCard({ id, icon: Icon, color, title, children }: {
  id: string
  icon: React.ElementType
  color: string
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="card p-5">
      <SectionAnchor id={id} />
      <div className="flex items-center gap-3 mb-4">
        <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" style={{ background: `${color}15` }}>
          <Icon size={17} style={{ color }} />
        </div>
        <h2 className="text-base font-semibold text-[#e2e2f0]">{title}</h2>
      </div>
      <div className="space-y-4 text-xs text-[#a0a0c0] leading-relaxed">
        {children}
      </div>
    </div>
  )
}

function SubSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-xs font-semibold text-[#e2e2f0] mb-2">{title}</h3>
      <div className="space-y-2 text-xs text-[#a0a0c0] leading-relaxed">
        {children}
      </div>
    </div>
  )
}

function Step({ n, children }: { n: number; children: React.ReactNode }) {
  return (
    <div className="flex gap-3">
      <div className="w-5 h-5 rounded-full bg-[#9b6dff]/20 border border-[#9b6dff]/30 flex items-center justify-center shrink-0 mt-0.5">
        <span className="text-[10px] font-bold text-[#9b6dff]">{n}</span>
      </div>
      <div className="flex-1 text-xs text-[#a0a0c0] leading-relaxed">{children}</div>
    </div>
  )
}

function ApiKeyCard({ name, badge, badgeColor, href, children }: {
  name: string
  badge: string
  badgeColor: string
  href: string
  children: React.ReactNode
}) {
  return (
    <div className="card-inset p-3 rounded-lg">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-semibold text-[#e2e2f0]">{name}</span>
        <span className="text-[10px] px-2 py-0.5 rounded-full font-medium" style={{ background: `${badgeColor}18`, color: badgeColor }}>
          {badge}
        </span>
        <a href={href} target="_blank" rel="noopener noreferrer" className="ml-auto text-[10px] text-[#9b6dff] hover:text-[#b48fff] underline underline-offset-2">
          Sign up →
        </a>
      </div>
      <div className="text-xs text-[#a0a0c0] leading-relaxed space-y-1">
        {children}
      </div>
    </div>
  )
}

function ConfigRow({ field, type, desc }: { field: string; type: string; desc: string }) {
  return (
    <tr className="border-b border-[#1e1e3a]">
      <td className="py-2 pr-3 font-mono text-[11px] text-[#9b6dff] align-top whitespace-nowrap">{field}</td>
      <td className="py-2 pr-3 text-[10px] text-[#6b6b8a] align-top whitespace-nowrap">{type}</td>
      <td className="py-2 text-[11px] text-[#a0a0c0] leading-relaxed">{desc}</td>
    </tr>
  )
}

// ─── Glossary accordion (ported from Glossary.tsx) ───────────────────────────

interface GlossaryAccordionProps {
  title: string
  subtitle: string
  icon: React.ElementType
  color: string
  defaultOpen?: boolean
  children: React.ReactNode
}

function GlossarySection({ title, subtitle, icon: Icon, color, defaultOpen = false, children }: GlossaryAccordionProps) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="card overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 p-4 text-left hover:bg-[#1a1a30] transition-colors"
      >
        <div className="w-10 h-10 rounded-lg shrink-0 flex items-center justify-center" style={{ background: `${color}15` }}>
          <Icon size={18} style={{ color }} />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-[#e2e2f0]">{title}</h3>
          <p className="text-[11px] text-[#6b6b8a] mt-0.5">{subtitle}</p>
        </div>
        <div className="text-[#6b6b8a] shrink-0 transition-transform" style={{ transform: open ? 'rotate(0)' : 'rotate(-90deg)' }}>
          <ChevronDown size={16} />
        </div>
      </button>
      {open && (
        <div className="px-4 pb-4 pt-1 border-t border-[#1e1e3a] space-y-2">
          {children}
        </div>
      )}
    </div>
  )
}

interface GlossaryItemProps {
  term: string
  children: React.ReactNode
  defaultOpen?: boolean
}

function GlossaryItem({ term, children, defaultOpen = false }: GlossaryItemProps) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="rounded-lg border border-[#1e1e3a] overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-[#0f0f1e] transition-colors"
      >
        <span className="text-[#6b6b8a] shrink-0">
          {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
        <span className="text-xs font-semibold text-[#e2e2f0]">{term}</span>
      </button>
      {open && (
        <div className="px-3 pb-3 pt-0 text-xs text-[#a0a0c0] leading-relaxed space-y-2">
          {children}
        </div>
      )}
    </div>
  )
}

function ExampleBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-2 px-3 py-2.5 rounded-lg bg-[#0f0f1e] border border-[#1e1e3a] text-[11px] font-mono text-[#a0a0c0] leading-relaxed">
      {children}
    </div>
  )
}

function GlossaryTip({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-2 px-3 py-2.5 rounded-lg bg-[#9b6dff]/5 border border-[#9b6dff]/15 text-[11px] text-[#c0b0e0] leading-relaxed flex gap-2">
      <Lightbulb size={12} className="text-[#9b6dff] shrink-0 mt-0.5" />
      <div>{children}</div>
    </div>
  )
}

// ─── Table of Contents ───────────────────────────────────────────────────────

const TOC_ITEMS = [
  { id: 'overview', label: 'Overview' },
  { id: 'quickstart-docker', label: 'Quick Start — Docker' },
  { id: 'quickstart-manual', label: 'Quick Start — Manual' },
  { id: 'api-keys', label: 'API Keys' },
  { id: 'model', label: 'How the Model Works' },
  { id: 'tabs', label: 'Dashboard Tabs' },
  { id: 'nas', label: 'NAS Deployment' },
  { id: 'config', label: 'Configuration Reference' },
  { id: 'troubleshooting', label: 'Troubleshooting' },
  { id: 'glossary', label: 'Glossary & Guide' },
]

// ─── Main page ───────────────────────────────────────────────────────────────

export default function Documentation() {
  return (
    <div className="px-4 md:px-8 py-6 max-w-3xl mx-auto">

      {/* ── Page header ── */}
      <div className="mb-2">
        <div className="flex items-center gap-2.5 mb-1">
          <BookOpen size={20} className="text-[#9b6dff]" />
          <h1 className="text-xl font-semibold text-[#e2e2f0]">Kalshi Betting Intelligence</h1>
        </div>
        <p className="text-xs text-[#6b6b8a]">AI-powered football betting signals using statistical models</p>
      </div>

      {/* ── Table of Contents ── */}
      <div className="card card-inset p-4 mb-6">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[#6b6b8a] mb-2">On this page</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1">
          {TOC_ITEMS.map((item) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              className="text-xs text-[#9b6dff] hover:text-[#b48fff] transition-colors"
            >
              → {item.label}
            </a>
          ))}
        </div>
      </div>

      <div className="space-y-4">

        {/* ── Overview ── */}
        <SectionCard id="overview" icon={HelpCircle} color="#5b8def" title="Overview">
          <p>
            Football Intel is a soccer betting intelligence dashboard. It connects to live prediction markets on{' '}
            <a href="https://kalshi.com" target="_blank" rel="noopener noreferrer" className="text-[#9b6dff] hover:text-[#b48fff]">Kalshi</a>{' '}
            — a regulated US exchange — and uses a calibrated statistical model to find bets where the market price is wrong. When the model
            says a team has a 65% chance of winning but the market is only pricing them at 43%, that's a potential edge. The dashboard
            surfaces these opportunities in real time, logs simulated $10 paper trades, and tracks the model's accuracy and profitability over time.
          </p>

          <SubSection title="How it works">
            <div className="flex flex-col gap-2">
              {[
                ['Fetch match data', 'Historical results (last 12 months) are pulled from football-data.org and cached locally.'],
                ['Calibrate model', 'A Poisson model is fitted to each team\'s attack and defense ratings, adjusted for home/away splits and recency.'],
                ['Scan Kalshi markets', 'Live market prices are fetched for all EPL, Bundesliga, and UCL match contracts.'],
                ['Generate signals', 'Matches where model probability exceeds market price by ≥5% are flagged as betting opportunities.'],
              ].map(([step, desc], i) => (
                <Step key={i} n={i + 1}>
                  <strong className="text-[#e2e2f0]">{step}</strong> — {desc}
                </Step>
              ))}
            </div>
          </SubSection>

          <SubSection title="Supported leagues">
            <ul className="space-y-1">
              <li>🏴󠁧󠁢󠁥󠁮󠁧󠁿 <strong className="text-[#e2e2f0]">English Premier League (EPL)</strong> — ~380 matches/season, 20 clubs</li>
              <li>🇩🇪 <strong className="text-[#e2e2f0]">Bundesliga</strong> — ~306 matches/season, 18 clubs</li>
              <li>🌍 <strong className="text-[#e2e2f0]">UEFA Champions League (UCL)</strong> — ~189 matches/season, 36 clubs</li>
            </ul>
            <Note>Kalshi currently offers per-match markets only for these three leagues. More leagues will be added as Kalshi expands its soccer offerings.</Note>
          </SubSection>
        </SectionCard>

        {/* ── Quick Start: Docker ── */}
        <SectionCard id="quickstart-docker" icon={Rocket} color="#3ddc84" title="Quick Start — Docker (Recommended)">
          <p>The easiest way to run Football Intel, perfect for a NAS or home server.</p>

          <Step n={1}>
            <strong className="text-[#e2e2f0]">Clone or download the project</strong>
            <CodeBlock>git clone https://github.com/your-username/football_intel.git{'\n'}cd football_intel</CodeBlock>
          </Step>

          <Step n={2}>
            <strong className="text-[#e2e2f0]">Copy the example config</strong>
            <CodeBlock>cp config/config.yaml.example config/config.yaml</CodeBlock>
          </Step>

          <Step n={3}>
            <strong className="text-[#e2e2f0]">Get your API keys</strong> — see the <a href="#api-keys" className="text-[#9b6dff] hover:text-[#b48fff]">API Keys section</a> below for instructions on signing up for each service.
          </Step>

          <Step n={4}>
            <strong className="text-[#e2e2f0]">Fill in <InlineCode>config/config.yaml</InlineCode></strong> with your API keys and key file paths. See the <a href="#config" className="text-[#9b6dff] hover:text-[#b48fff]">Configuration Reference</a> for all fields.
          </Step>

          <Step n={5}>
            <strong className="text-[#e2e2f0]">Build and start the container</strong>
            <CodeBlock>docker-compose up -d</CodeBlock>
            The first build downloads ~600 MB of layers and compiles the frontend. Subsequent starts are instant.
          </Step>

          <Step n={6}>
            <strong className="text-[#e2e2f0]">Open the dashboard</strong>
            <CodeBlock>http://your-nas-ip:8080</CodeBlock>
            Replace <InlineCode>your-nas-ip</InlineCode> with your server's local IP address (e.g. <InlineCode>192.168.1.50</InlineCode>).
          </Step>

          <Note>Signals are cached for 15 minutes. The first page load triggers a live pipeline run which may take 10–30 seconds depending on your internet speed.</Note>
        </SectionCard>

        {/* ── Quick Start: Manual ── */}
        <SectionCard id="quickstart-manual" icon={FileText} color="#f5a623" title="Quick Start — Manual (No Docker)">
          <p>Run the backend and frontend separately — useful for local development or machines without Docker.</p>

          <SubSection title="Prerequisites">
            <ul className="space-y-1">
              <li>Python <strong className="text-[#e2e2f0]">3.10+</strong></li>
              <li>Node.js <strong className="text-[#e2e2f0]">20+</strong> and npm</li>
            </ul>
          </SubSection>

          <Step n={1}>
            <strong className="text-[#e2e2f0]">Install Python dependencies</strong>
            <CodeBlock>cd football_intel{'\n'}pip install -r requirements.txt</CodeBlock>
          </Step>

          <Step n={2}>
            <strong className="text-[#e2e2f0]">Build the frontend</strong>
            <CodeBlock>cd web{'\n'}npm install{'\n'}npm run build</CodeBlock>
          </Step>

          <Step n={3}>
            <strong className="text-[#e2e2f0]">Copy and fill in the config</strong>
            <CodeBlock>cp config/config.yaml.example config/config.yaml{'\n'}# then edit config/config.yaml with your API keys</CodeBlock>
          </Step>

          <Step n={4}>
            <strong className="text-[#e2e2f0]">Run the API server</strong> (from the parent directory of <InlineCode>football_intel/</InlineCode>):
            <CodeBlock>uvicorn football_intel.api.main:app --host 0.0.0.0 --port 8000</CodeBlock>
            Then open <InlineCode>http://localhost:8000</InlineCode> in your browser.
          </Step>

          <Note>For development with hot-reload: run <InlineCode>uvicorn ... --reload</InlineCode> and separately run <InlineCode>cd web && npm run dev</InlineCode> to get Vite's dev server on port 5173 with HMR.</Note>
        </SectionCard>

        {/* ── API Keys ── */}
        <SectionCard id="api-keys" icon={Settings} color="#9b6dff" title="API Keys Required">
          <div className="space-y-3">
            <ApiKeyCard
              name="Football-Data.org"
              badge="Required · Free"
              badgeColor="#3ddc84"
              href="https://www.football-data.org/"
            >
              <p>Provides historical match results used to calibrate the Poisson model. Free tier: 10 requests/minute, includes PL, BL1, and CL (Champions League).</p>
              <ol className="list-decimal list-inside space-y-1 mt-2">
                <li>Sign up at <a href="https://www.football-data.org/" target="_blank" rel="noopener noreferrer" className="text-[#9b6dff] hover:text-[#b48fff]">football-data.org</a></li>
                <li>Copy your API token from the dashboard</li>
                <li>Set <InlineCode>football_data.api_key</InlineCode> in config.yaml</li>
              </ol>
            </ApiKeyCard>

            <ApiKeyCard
              name="Kalshi"
              badge="Required · Free account"
              badgeColor="#3ddc84"
              href="https://kalshi.com"
            >
              <p>Provides live market prices for soccer match contracts — this is what the model compares against.</p>
              <ol className="list-decimal list-inside space-y-1 mt-2">
                <li>Sign up at <a href="https://kalshi.com" target="_blank" rel="noopener noreferrer" className="text-[#9b6dff] hover:text-[#b48fff]">kalshi.com</a></li>
                <li>Go to <strong className="text-[#e2e2f0]">Settings → API Keys</strong> and generate a new key</li>
                <li>Download the RSA private key <InlineCode>.key</InlineCode> file and save it somewhere permanent</li>
                <li>Set <InlineCode>kalshi.key_id</InlineCode> (the UUID) and <InlineCode>kalshi.private_key_path</InlineCode> in config.yaml</li>
              </ol>
              <Note>Use the <strong>demo API</strong> (<InlineCode>demo-api.kalshi.co</InlineCode>) for testing — prices are simulated. Switch to <InlineCode>api.elections.kalshi.com</InlineCode> for live data.</Note>
            </ApiKeyCard>

            <ApiKeyCard
              name="The Odds API"
              badge="Optional · 500 req/month free"
              badgeColor="#f5a623"
              href="https://the-odds-api.com"
            >
              <p>Additional odds sources from bookmakers worldwide. Used as a secondary data point — not required for core functionality.</p>
              <ol className="list-decimal list-inside space-y-1 mt-2">
                <li>Sign up at <a href="https://the-odds-api.com" target="_blank" rel="noopener noreferrer" className="text-[#9b6dff] hover:text-[#b48fff]">the-odds-api.com</a></li>
                <li>Copy your API key from the dashboard</li>
                <li>Set <InlineCode>odds_api.api_key</InlineCode> in config.yaml</li>
              </ol>
            </ApiKeyCard>

            <ApiKeyCard
              name="Telegram Bot"
              badge="Optional · Free"
              badgeColor="#6b6b8a"
              href="https://t.me/BotFather"
            >
              <p>Sends signal alerts to a Telegram chat when new high-edge opportunities appear.</p>
              <ol className="list-decimal list-inside space-y-1 mt-2">
                <li>Open Telegram and message <a href="https://t.me/BotFather" target="_blank" rel="noopener noreferrer" className="text-[#9b6dff] hover:text-[#b48fff]">@BotFather</a></li>
                <li>Send <InlineCode>/newbot</InlineCode> and follow the prompts to create a bot</li>
                <li>Copy the bot token (format: <InlineCode>123456:ABC-DEF...</InlineCode>)</li>
                <li>Start a chat with your bot, then get your chat ID by messaging <a href="https://t.me/userinfobot" target="_blank" rel="noopener noreferrer" className="text-[#9b6dff] hover:text-[#b48fff]">@userinfobot</a></li>
                <li>Set <InlineCode>telegram.bot_token</InlineCode> and <InlineCode>telegram.chat_id</InlineCode> in config.yaml</li>
              </ol>
            </ApiKeyCard>
          </div>
        </SectionCard>

        {/* ── How the Model Works ── */}
        <SectionCard id="model" icon={Cpu} color="#9b6dff" title="How the Model Works">
          <p>
            The prediction engine is a <strong className="text-[#e2e2f0]">calibrated Poisson model with Dixon-Coles correction</strong>.
            In plain terms: it uses historical goal-scoring patterns to estimate how many goals each team will score, then calculates
            the probability of every possible scoreline, and from those derives all the bet-type probabilities.
          </p>

          <SubSection title="The Poisson goal model">
            <p>Goals in soccer are relatively rare, independent events — which means they follow a Poisson distribution almost perfectly.
            If we know the expected goals (λ) for each team, we can calculate <InlineCode>P(0-0)</InlineCode>, <InlineCode>P(1-0)</InlineCode>,
            <InlineCode>P(2-1)</InlineCode>, etc., then sum them up into any bet type.</p>
            <CodeBlock>
              {'λ_home = league_avg_home_goals × home_attack × away_defense\n'}
              {'λ_away = league_avg_away_goals × away_attack × home_defense\n\n'}
              {'P(home=2, away=1) = Poisson(2 | λ_home) × Poisson(1 | λ_away)\n'}
              {'P(home wins) = sum of all scorelines where home > away'}
            </CodeBlock>
          </SubSection>

          <SubSection title="Per-team strength ratings">
            <p>Each team gets four ratings fitted from its last 12 months of results:</p>
            <ul className="space-y-1">
              <li><strong className="text-[#e2e2f0]">Attack Home / Away</strong> — how many goals they score at home vs away, relative to the league average</li>
              <li><strong className="text-[#e2e2f0]">Defense Home / Away</strong> — how many goals they concede, relative to the league average</li>
            </ul>
            <p>A rating of <InlineCode>1.0</InlineCode> = exactly average. <InlineCode>1.8</InlineCode> = 80% above average.</p>
          </SubSection>

          <SubSection title="Recency weighting">
            <p>Matches from 60+ days ago have half the weight of recent matches. This means the model responds to form shifts — a team that's been on a bad run will see its ratings drift down faster than if all history were treated equally.</p>
          </SubSection>

          <SubSection title="Key signal metrics explained">
            <div className="space-y-2">
              {[
                ['Lambda (λ)', 'Expected goals for a team in this specific match. λ_home = 2.1 means the model expects the home side to score about 2 goals.'],
                ['Edge', 'Model probability minus Kalshi market price. Edge = 22% means the model thinks the event is 22 percentage points more likely than the market does.'],
                ['Confidence', 'Based on how many historical matches are in the database for both teams. HIGH = 20+ matches each. LOW = fewer than 10 matches.'],
                ['Score (0–100)', 'Edge × 200, capped at 100. A quick single-number strength rating — the bigger the edge, the higher the score.'],
              ].map(([term, desc]) => (
                <div key={term as string} className="card-inset p-2.5 rounded-lg">
                  <span className="text-[11px] font-semibold text-[#e2e2f0]">{term}</span>
                  <p className="text-[11px] text-[#a0a0c0] mt-0.5">{desc as string}</p>
                </div>
              ))}
            </div>
          </SubSection>
        </SectionCard>

        {/* ── Dashboard Tabs ── */}
        <SectionCard id="tabs" icon={Microscope} color="#5b8def" title="Dashboard Tabs">
          <div className="space-y-2">
            {[
              [Zap, '#9b6dff', 'Active Signals', 'Current betting opportunities. Shows every match where the model finds ≥5% edge over the Kalshi market price. Cards update every 15 minutes. Click any card to go directly to the Kalshi market.'],
              [TrendingUp, '#3ddc84', 'Performance', 'Win rate, ROI, cumulative PnL chart, max drawdown, and weekly breakdown. This is where you evaluate whether the model is actually making money over time.'],
              [FileText, '#f5a623', 'Trade Log', 'Full history of every paper trade the system has logged — with timestamps, match details, stake, odds, and outcome. Filterable by status (pending / win / lose).'],
              [Microscope, '#5b8def', 'Model Insights', 'Deep-dive view per match: goal lambdas, team strength ratings, scoreline probability matrix, goal distribution chart, and all flagged signals for that game.'],
              [BookOpen, '#9b6dff', 'Docs (this page)', 'Full documentation, glossary of betting terms, and deployment guide. You\'re here!'],
            ].map(([Icon, color, label, desc]) => (
              <div key={label as string} className="card-inset p-3 rounded-lg flex gap-3">
                <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5" style={{ background: `${color as string}15` }}>
                  {/* @ts-ignore */}
                  <Icon size={14} style={{ color }} />
                </div>
                <div>
                  <p className="text-xs font-semibold text-[#e2e2f0]">{label as string}</p>
                  <p className="text-[11px] text-[#a0a0c0] leading-relaxed mt-0.5">{desc as string}</p>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        {/* ── NAS Deployment ── */}
        <SectionCard id="nas" icon={Server} color="#f5a623" title="NAS Deployment Tips">
          <p>Football Intel runs great on a home NAS — it uses minimal resources (under 256 MB RAM at idle) and runs 24/7 without needing a laptop on.</p>

          <SubSection title="Synology NAS">
            <ol className="list-decimal list-inside space-y-1">
              <li>Install <strong className="text-[#e2e2f0]">Container Manager</strong> from Package Center</li>
              <li>Go to Container Manager → <strong className="text-[#e2e2f0]">Project</strong> → Create</li>
              <li>Upload or paste the <InlineCode>docker-compose.yml</InlineCode> contents</li>
              <li>Set the project path to your <InlineCode>football_intel/</InlineCode> folder</li>
              <li>Click Build &amp; Start</li>
            </ol>
          </SubSection>

          <SubSection title="QNAP NAS">
            <ol className="list-decimal list-inside space-y-1">
              <li>Open <strong className="text-[#e2e2f0]">Container Station</strong></li>
              <li>Go to Create → Create Application</li>
              <li>Paste the <InlineCode>docker-compose.yml</InlineCode> contents and click Validate → Create</li>
            </ol>
          </SubSection>

          <SubSection title="Unraid">
            <ol className="list-decimal list-inside space-y-1">
              <li>Install the <strong className="text-[#e2e2f0]">Community Applications</strong> plugin</li>
              <li>Use the Docker Compose manager or the built-in Docker tab to add a custom container</li>
              <li>Point it at the <InlineCode>football_intel/</InlineCode> folder with <InlineCode>docker-compose.yml</InlineCode></li>
            </ol>
          </SubSection>

          <SubSection title="Persistent data">
            <p>The docker-compose file mounts two volumes so your data survives container rebuilds:</p>
            <ul className="space-y-1">
              <li><InlineCode>./config/</InlineCode> → your API keys and config.yaml</li>
              <li><InlineCode>./data/</InlineCode> → the SQLite trade database and signal history</li>
            </ul>
            <Note>Never put <InlineCode>config.yaml</InlineCode> or your Kalshi <InlineCode>.key</InlineCode> file inside the Docker image — always mount them as volumes so they're not baked into the build.</Note>
          </SubSection>

          <SubSection title="Auto-start on boot">
            <p>The <InlineCode>restart: unless-stopped</InlineCode> policy in docker-compose.yml means the container will automatically restart after a reboot or crash — no manual intervention needed.</p>
          </SubSection>
        </SectionCard>

        {/* ── Configuration Reference ── */}
        <SectionCard id="config" icon={Settings} color="#6b6b8a" title="Configuration Reference">
          <p>Copy <InlineCode>config/config.yaml.example</InlineCode> to <InlineCode>config/config.yaml</InlineCode> and fill in the values below.</p>

          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-xs">
              <thead>
                <tr className="border-b border-[#2a2a4a]">
                  <th className="py-2 pr-3 text-left text-[10px] font-semibold text-[#6b6b8a] uppercase tracking-wider">Field</th>
                  <th className="py-2 pr-3 text-left text-[10px] font-semibold text-[#6b6b8a] uppercase tracking-wider">Type</th>
                  <th className="py-2 text-left text-[10px] font-semibold text-[#6b6b8a] uppercase tracking-wider">Description</th>
                </tr>
              </thead>
              <tbody>
                <ConfigRow field="football_data.api_key" type="string" desc="Your football-data.org API token. Required." />
                <ConfigRow field="football_data.base_url" type="string" desc="API base URL. Default: https://api.football-data.org/v4" />
                <ConfigRow field="football_data.leagues" type="list" desc="League codes to fetch. Use ALL for all free-tier leagues, or specify PL, BL1, CL, etc." />
                <ConfigRow field="kalshi.key_id" type="string" desc="UUID from Kalshi API Keys page. Required." />
                <ConfigRow field="kalshi.private_key_path" type="string" desc="Absolute path to your RSA private key file (.key). Required." />
                <ConfigRow field="kalshi.base_url" type="string" desc="Kalshi API endpoint. Use demo-api.kalshi.co for testing, api.elections.kalshi.com for live." />
                <ConfigRow field="telegram.bot_token" type="string" desc="Telegram bot token from @BotFather. Optional." />
                <ConfigRow field="telegram.chat_id" type="string" desc="Telegram chat ID for signal alerts. Optional." />
                <ConfigRow field="odds_api.api_key" type="string" desc="The Odds API key. Optional." />
                <ConfigRow field="odds_api.regions" type="string" desc="Bookmaker regions: uk, eu, us, au. Default: uk,eu" />
                <ConfigRow field="storage.db_path" type="string" desc="SQLite database file path. Default: football_intel/data/football_intel.db" />
                <ConfigRow field="storage.cache_ttl_hours" type="int" desc="How long to cache historical match data before re-fetching. Default: 6" />
                <ConfigRow field="logging.level" type="string" desc="Log level: DEBUG, INFO, WARNING, ERROR. Default: INFO" />
                <ConfigRow field="logging.log_file" type="string" desc="Path to the log file. Default: football_intel/logs/system.log" />
              </tbody>
            </table>
          </div>
        </SectionCard>

        {/* ── Troubleshooting ── */}
        <SectionCard id="troubleshooting" icon={Wrench} color="#e84040" title="Troubleshooting">
          <div className="space-y-3">
            {[
              ['"Missing config.yaml"', 'The app can\'t find its configuration. Copy the example file: cp config/config.yaml.example config/config.yaml — then fill in your API keys.'],
              ['"Kalshi auth failed" / 401 error', 'Check that kalshi.key_id matches the UUID on your Kalshi API Keys page, and that private_key_path points to the correct .key file. The path must be accessible inside the container (use the mounted volume path).'],
              ['"No signals showing" on Active Signals', 'The model needs historical data before it can generate signals. On first run, it fetches ~12 months of match results which can take a minute. Signals also only appear when the model finds ≥5% edge over the current Kalshi market price — during quiet market periods there may be fewer opportunities.'],
              ['Container won\'t start', 'Check the logs: docker logs football-intel. Common causes: missing config.yaml (it\'s gitignored), wrong volume paths, or a bad Kalshi key file.'],
              ['Dashboard shows "Pipeline error"', 'Usually a network issue fetching from Kalshi or football-data.org. Check your API keys are valid and that the container has internet access. Try docker logs football-intel for the full stack trace.'],
              ['TypeScript / build errors (manual setup)', 'Make sure you\'re running Node 20+ (check with node --version). Delete web/node_modules and run npm install again. If the issue persists, check the console output from npm run build.'],
            ].map(([issue, fix]) => (
              <div key={issue as string} className="card-inset p-3 rounded-lg">
                <p className="text-[11px] font-semibold text-[#e2e2f0] mb-1">{issue as string}</p>
                <p className="text-[11px] text-[#a0a0c0] leading-relaxed">{fix as string}</p>
              </div>
            ))}
          </div>

          <div className="mt-3 p-3 rounded-lg bg-[#0a0a12] border border-[#1e1e3a]">
            <p className="text-[10px] font-semibold text-[#6b6b8a] uppercase tracking-wider mb-1">Useful debug commands</p>
            <CodeBlock>
              {'# View container logs\n'}
              {'docker logs football-intel\n\n'}
              {'# Follow live logs\n'}
              {'docker logs -f football-intel\n\n'}
              {'# Check container status\n'}
              {'docker ps\n\n'}
              {'# Restart the container\n'}
              {'docker-compose restart\n\n'}
              {'# Rebuild from scratch\n'}
              {'docker-compose down && docker-compose up --build -d'}
            </CodeBlock>
          </div>
        </SectionCard>

        {/* ── Glossary (ported from Glossary.tsx) ── */}
        <div>
          <SectionAnchor id="glossary" />
          <div className="flex items-center gap-2.5 mb-3 mt-2">
            <BookOpen size={16} className="text-[#9b6dff]" />
            <h2 className="text-base font-semibold text-[#e2e2f0]">Glossary &amp; Guide</h2>
          </div>
          <p className="text-xs text-[#6b6b8a] mb-4">
            New to sports betting or prediction markets? Start here. Click any section to expand it, then click individual terms to learn more.
          </p>

          <div className="space-y-3">

            <GlossarySection
              title="What Is This Dashboard?"
              subtitle="The big picture — what this tool does and why it exists"
              icon={HelpCircle}
              color="#5b8def"
              defaultOpen={false}
            >
              <GlossaryItem term="What does Football Intel do?" defaultOpen={false}>
                <p>Football Intel is a <strong className="text-[#e2e2f0]">soccer betting intelligence tool</strong>. It scans prediction markets on Kalshi (a regulated US exchange), compares market prices against a statistical model, and finds bets where the model thinks the market is wrong.</p>
                <p className="mt-2">Think of it like a price comparison tool, but for probabilities. If the market says "Brighton has a 43% chance of winning" but our model calculates 65%, that's a potential opportunity. The dashboard shows you these opportunities and tracks how accurate the model is over time.</p>
                <GlossaryTip>This is a research and paper-trading tool. No real money is being wagered. All trades shown are simulated $10 bets to evaluate model performance.</GlossaryTip>
              </GlossaryItem>

              <GlossaryItem term="What is Kalshi?">
                <p>Kalshi is a <strong className="text-[#e2e2f0]">federally regulated prediction market exchange</strong> in the United States (regulated by the CFTC). Instead of traditional sportsbook odds, Kalshi uses binary contracts that trade between $0 and $1.</p>
                <p className="mt-2">You buy a contract at a price (e.g., 43¢) and it either pays out $1 if the event happens, or $0 if it doesn't. The price naturally represents the market's consensus probability of the event.</p>
                <ExampleBox>
                  "Chelsea to win" priced at <span className="text-[#9b6dff]">43¢</span><br />
                  → If Chelsea wins: you get $1 back (profit of <span className="text-[#3ddc84]">57¢</span>)<br />
                  → If Chelsea doesn't win: you lose your <span className="text-[#e84040]">43¢</span>
                </ExampleBox>
                <GlossaryTip>Unlike traditional sportsbooks, Kalshi is an exchange — you're trading against other people, not against the house.</GlossaryTip>
              </GlossaryItem>

              <GlossaryItem term="What is a prediction market?">
                <p>A prediction market is a place where people buy and sell contracts based on the outcome of real-world events. The prices of these contracts reflect the crowd's collective belief about how likely each outcome is.</p>
                <p className="mt-2">If lots of people think Arsenal will win, the "Arsenal wins" contract price goes up. This makes the price a useful indicator of probability — but it's not always accurate, which is where our model comes in.</p>
              </GlossaryItem>

              <GlossaryItem term="What is paper trading?">
                <p>Paper trading means <strong className="text-[#e2e2f0]">tracking hypothetical bets without risking real money</strong>. Every signal this dashboard generates is logged as if you'd placed a $10 bet, and we track whether it would have won or lost.</p>
                <ExampleBox>
                  Signal: "Brighton to win" at 43¢<br />
                  Paper trade: $10 bet at odds 2.33<br />
                  → If Brighton wins: +$13.26 logged to your PnL<br />
                  → If Brighton loses: -$10.00 logged to your PnL
                </ExampleBox>
              </GlossaryItem>
            </GlossarySection>

            <GlossarySection
              title="Reading Signal Cards"
              subtitle="How to interpret every part of an Active Signal card"
              icon={Zap}
              color="#9b6dff"
            >
              <GlossaryItem term="Entry Price (in cents)">
                <p>The <strong className="text-[#e2e2f0]">cost to buy one contract</strong> on Kalshi, shown in cents. If Entry is 43¢, the market is saying "there's a 43% chance this happens."</p>
                <ExampleBox>
                  <span className="text-[#9b6dff]">Entry: 43¢</span> = Market says 43% probability<br />
                  <span className="text-[#9b6dff]">Entry: 12¢</span> = Market says only 12% probability (long shot)<br />
                  <span className="text-[#9b6dff]">Entry: 85¢</span> = Market says 85% probability (heavy favorite)
                </ExampleBox>
              </GlossaryItem>

              <GlossaryItem term="Upside (in cents)">
                <p>How much you'd <strong className="text-[#e2e2f0]">profit per contract</strong> if the bet wins. Since every Kalshi contract pays $1 if correct, Upside = 100¢ minus Entry.</p>
                <ExampleBox>
                  Entry 43¢ → Upside <span className="text-[#3ddc84]">+57¢</span><br />
                  Entry 12¢ → Upside <span className="text-[#3ddc84]">+88¢</span><br />
                  Entry 85¢ → Upside <span className="text-[#3ddc84]">+15¢</span>
                </ExampleBox>
              </GlossaryItem>

              <GlossaryItem term="Edge">
                <p>The <strong className="text-[#e2e2f0]">core metric</strong> — the difference between what our model predicts and what the market prices. A positive edge means our model thinks the outcome is more likely than the market does.</p>
                <ExampleBox>
                  Our model: Brighton has a 65% chance<br />
                  Kalshi market: Brighton priced at 43%<br />
                  Edge = 65% − 43% = <span className="text-[#3ddc84]">+22%</span>
                </ExampleBox>
              </GlossaryItem>

              <GlossaryItem term="Score (0–100)">
                <p>A quick-glance signal strength rating. Calculated as <InlineCode>min(Edge × 200, 100)</InlineCode>. Higher = stronger disagreement with the market.</p>
              </GlossaryItem>

              <GlossaryItem term="Confidence Level">
                <p>How trustworthy the prediction is, based on how much historical data we have.</p>
                <ExampleBox>
                  <span className="text-[#3ddc84] font-semibold">HIGH</span> — 20+ matches for both teams<br />
                  <span className="text-[#f5a623] font-semibold">MEDIUM</span> — 10–19 matches<br />
                  <span className="text-[#e84040] font-semibold">LOW</span> — Fewer than 10 matches (treat with skepticism)
                </ExampleBox>
              </GlossaryItem>

              <GlossaryItem term="LEAN vs STRONG Badges">
                <p>
                  <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-[#f5a623]/20 text-[#f5a623] mr-2">LEAN</span>
                  Edge under 20% — moderate disagreement with the market.
                </p>
                <p className="mt-2">
                  <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-[#e84040]/20 text-[#e84040] mr-2">STRONG</span>
                  Edge 20% or higher — significant mispricing detected.
                </p>
              </GlossaryItem>
            </GlossarySection>

            <GlossarySection
              title="Types of Bets"
              subtitle="The different ways you can bet on a soccer match"
              icon={Trophy}
              color="#f5a623"
            >
              <GlossaryItem term="MONEYLINE (Match Winner)">
                <p>Who wins the match? In soccer, this is a 3-way bet (home win / draw / away win).</p>
              </GlossaryItem>

              <GlossaryItem term="OVER_UNDER (Total Goals)">
                <p>Will the total goals scored exceed a line? Over 2.5 means 3+ total goals required.</p>
                <ExampleBox>
                  Over 2.5 at 55¢ → WIN if score is 2-1, 3-0, 2-2, etc.<br />
                  Over 2.5 at 55¢ → LOSE if score is 1-0, 0-0, 1-1, etc.
                </ExampleBox>
              </GlossaryItem>

              <GlossaryItem term="SPREAD (Goal Margin)">
                <p>Will a team win by more than a specific margin? "Bayern wins by 2+" loses if Bayern wins 1-0.</p>
              </GlossaryItem>

              <GlossaryItem term="BTTS (Both Teams to Score)">
                <p>Will both teams score at least one goal? Yes wins on scores like 1-1, 2-1, 1-2. No wins on 1-0, 0-0, 2-0, etc.</p>
              </GlossaryItem>

              <GlossaryItem term="FIRST_HALF (First Half Winner)">
                <p>Like a moneyline but only the first 45 minutes count. Draws at halftime are very common (~40–45% of matches).</p>
              </GlossaryItem>
            </GlossarySection>

            <GlossarySection
              title="Performance Metrics"
              subtitle="How to read the Performance page and track results"
              icon={TrendingUp}
              color="#3ddc84"
            >
              <GlossaryItem term="Win Rate">
                <p>Percentage of settled bets that won. A 40% win rate can be very profitable if you're betting on underpriced underdogs.</p>
              </GlossaryItem>

              <GlossaryItem term="ROI (Return on Investment)">
                <p>Total profit as a percentage of total staked. The most important metric for evaluating the model.</p>
                <ExampleBox>
                  Total staked: $500 · Profit: +$75<br />
                  ROI = <span className="text-[#3ddc84]">+15%</span> (very good — professional level is 3–10%)
                </ExampleBox>
              </GlossaryItem>

              <GlossaryItem term="Cumulative PnL Chart">
                <p>Running total of profit/loss over time. A steadily rising line = model is consistently finding profitable bets. Wild swings = high variance.</p>
              </GlossaryItem>

              <GlossaryItem term="Max Drawdown">
                <p>The largest drop from a peak to a trough in your PnL. Measures the worst losing streak in dollar terms. A good rule of thumb: drawdown should be smaller than total profit.</p>
              </GlossaryItem>
            </GlossarySection>

            <GlossarySection
              title="Model Accuracy"
              subtitle="How to tell if the model's predictions are reliable"
              icon={Target}
              color="#e84040"
            >
              <GlossaryItem term="Calibration Chart">
                <p>The most important chart for evaluating a prediction model. It answers: "When the model says 40%, does it actually happen ~40% of the time?"</p>
                <ExampleBox>
                  → Points on the diagonal = well-calibrated ✅<br />
                  → Points above diagonal = model is under-confident<br />
                  → Points below diagonal = model is over-confident ⚠️
                </ExampleBox>
                <GlossaryTip>You need at least 50–100 settled trades before calibration becomes meaningful.</GlossaryTip>
              </GlossaryItem>

              <GlossaryItem term="Rolling Win Rate">
                <p>A moving average of win rate over the last 10 trades. Trending upward = model is improving. Trending downward = may need recalibration.</p>
              </GlossaryItem>
            </GlossarySection>

            <GlossarySection
              title="Tips for Beginners"
              subtitle="Practical advice if you're new to prediction markets"
              icon={Lightbulb}
              color="#f5d623"
            >
              <GlossaryItem term="Start with paper trading" defaultOpen={false}>
                <p>Don't bet real money until you've tracked the model for at least 2–4 weeks. The Performance and Accuracy pages are your test drive.</p>
              </GlossaryItem>

              <GlossaryItem term="Losses are normal">
                <p>Even with a statistical edge, individual bets lose. What matters is long-term profitability across many bets — like a weighted coin that lands heads 60% of the time but still gets tails.</p>
              </GlossaryItem>

              <GlossaryItem term="Prioritize HIGH confidence signals">
                <p>These have the most historical data and the most reliable predictions. Be very cautious with LOW confidence signals — large edges with low confidence usually mean limited data, not genuine opportunity.</p>
              </GlossaryItem>

              <GlossaryItem term="Never bet more than you can afford to lose">
                <p className="text-[#e84040] font-semibold">🚫 This dashboard is a research tool, not financial advice. Always gamble responsibly.</p>
              </GlossaryItem>
            </GlossarySection>

          </div>
        </div>

      </div>

      {/* Footer */}
      <div className="mt-10 mb-4 text-center text-[10px] text-[#6b6b8a]">
        Football Intel · Calibrated Poisson Model · Data from{' '}
        <a href="https://football-data.org" target="_blank" rel="noopener noreferrer" className="text-[#9b6dff] hover:text-[#b48fff]">
          football-data.org
        </a>
        {' · '}
        <a href="https://kalshi.com" target="_blank" rel="noopener noreferrer" className="text-[#9b6dff] hover:text-[#b48fff]">
          Kalshi
        </a>
      </div>
    </div>
  )
}
