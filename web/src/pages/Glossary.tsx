import { useState } from 'react'
import { ChevronDown, ChevronRight, Zap, TrendingUp, Target, HelpCircle, Lightbulb, Trophy, PieChart } from 'lucide-react'

// ─── Accordion Components ───────────────────────────────────────────────────

interface AccordionSectionProps {
  title: string
  subtitle: string
  icon: React.ElementType
  color: string
  defaultOpen?: boolean
  children: React.ReactNode
}

function AccordionSection({ title, subtitle, icon: Icon, color, defaultOpen = false, children }: AccordionSectionProps) {
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
          <h2 className="text-sm font-semibold text-[#e2e2f0]">{title}</h2>
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

interface AccordionItemProps {
  term: string
  children: React.ReactNode
  defaultOpen?: boolean
}

function AccordionItem({ term, children, defaultOpen = false }: AccordionItemProps) {
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

function Tip({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-2 px-3 py-2.5 rounded-lg bg-[#9b6dff]/5 border border-[#9b6dff]/15 text-[11px] text-[#c0b0e0] leading-relaxed flex gap-2">
      <Lightbulb size={12} className="text-[#9b6dff] shrink-0 mt-0.5" />
      <div>{children}</div>
    </div>
  )
}

// ─── Main Page ──────────────────────────────────────────────────────────────

export default function Glossary() {
  return (
    <div className="px-4 md:px-8 py-6 max-w-3xl mx-auto">
      {/* Page header */}
      <div className="flex items-center gap-2.5 mb-2">
        <h1 className="text-xl font-semibold text-[#e2e2f0]">Glossary & Guide</h1>
      </div>
      <p className="text-xs text-[#6b6b8a] mb-6">
        New to sports betting or prediction markets? Start here. Click any section to expand it, then click individual terms to learn more.
      </p>

      <div className="space-y-3">

        {/* ── Section 1: What Is This Dashboard? ── */}
        <AccordionSection
          title="What Is This Dashboard?"
          subtitle="The big picture — what this tool does and why it exists"
          icon={HelpCircle}
          color="#5b8def"
          defaultOpen={true}
        >
          <AccordionItem term="What does Football Intel do?" defaultOpen={true}>
            <p>Football Intel is a <strong className="text-[#e2e2f0]">soccer betting intelligence tool</strong>. It scans prediction markets on Kalshi (a regulated US exchange), compares market prices against a statistical model, and finds bets where the model thinks the market is wrong.</p>
            <p className="mt-2">Think of it like a price comparison tool, but for probabilities. If the market says "Brighton has a 43% chance of winning" but our model calculates 65%, that's a potential opportunity. The dashboard shows you these opportunities and tracks how accurate the model is over time.</p>
            <Tip>This is a research and paper-trading tool. No real money is being wagered. All trades shown are simulated $10 bets to evaluate model performance.</Tip>
          </AccordionItem>

          <AccordionItem term="What is Kalshi?">
            <p>Kalshi is a <strong className="text-[#e2e2f0]">federally regulated prediction market exchange</strong> in the United States (regulated by the CFTC). Instead of traditional sportsbook odds, Kalshi uses binary contracts that trade between $0 and $1.</p>
            <p className="mt-2">You buy a contract at a price (e.g., 43¢) and it either pays out $1 if the event happens, or $0 if it doesn't. The price naturally represents the market's consensus probability of the event.</p>
            <ExampleBox>
              "Chelsea to win" priced at <span className="text-[#9b6dff]">43¢</span><br />
              → If Chelsea wins: you get $1 back (profit of <span className="text-[#3ddc84]">57¢</span>)<br />
              → If Chelsea doesn't win: you lose your <span className="text-[#e84040]">43¢</span>
            </ExampleBox>
            <Tip>Unlike traditional sportsbooks, Kalshi is an exchange — you're trading against other people, not against the house. This means prices are set by market supply and demand.</Tip>
          </AccordionItem>

          <AccordionItem term="What is a prediction market?">
            <p>A prediction market is a place where people buy and sell contracts based on the outcome of real-world events. The prices of these contracts reflect the crowd's collective belief about how likely each outcome is.</p>
            <p className="mt-2">For example, if lots of people think Arsenal will win, the "Arsenal wins" contract price goes up. If few people think they'll win, the price goes down. This makes the price a useful indicator of probability — but it's not always accurate, which is where our model comes in.</p>
          </AccordionItem>

          <AccordionItem term="What is paper trading?">
            <p>Paper trading means <strong className="text-[#e2e2f0]">tracking hypothetical bets without risking real money</strong>. Every signal this dashboard generates is logged as if you'd placed a $10 bet, and we track whether it would have won or lost.</p>
            <p className="mt-2">This lets you evaluate the model's accuracy and profitability before deciding whether to bet real money. Think of it like a flight simulator for betting — all the learning, none of the risk.</p>
            <ExampleBox>
              Signal: "Brighton to win" at 43¢<br />
              Paper trade: $10 bet at odds 2.33<br />
              → If Brighton wins: +$13.26 logged to your PnL<br />
              → If Brighton loses: -$10.00 logged to your PnL
            </ExampleBox>
          </AccordionItem>
        </AccordionSection>

        {/* ── Section 2: Reading Signal Cards ── */}
        <AccordionSection
          title="Reading Signal Cards"
          subtitle="How to interpret every part of an Active Signal card"
          icon={Zap}
          color="#9b6dff"
        >
          <AccordionItem term="Entry Price (in cents)">
            <p>The <strong className="text-[#e2e2f0]">cost to buy one contract</strong> on Kalshi, shown in cents. This is what the market collectively thinks the probability is.</p>
            <p className="mt-2">If Entry is 43¢, the market is saying "there's a 43% chance this happens." You'd pay 43¢ per contract, and if you're right, you get $1 back.</p>
            <ExampleBox>
              <span className="text-[#9b6dff]">Entry: 43¢</span> = Market says 43% probability<br />
              <span className="text-[#9b6dff]">Entry: 12¢</span> = Market says only 12% probability (long shot)<br />
              <span className="text-[#9b6dff]">Entry: 85¢</span> = Market says 85% probability (heavy favorite)
            </ExampleBox>
            <Tip>Lower entry = higher potential profit but lower chance of winning. Higher entry = lower profit but higher chance. The model helps you find where the market has the probability wrong.</Tip>
          </AccordionItem>

          <AccordionItem term="Upside (in cents)">
            <p>How much you'd <strong className="text-[#e2e2f0]">profit per contract</strong> if the bet wins. Since every Kalshi contract pays $1 if correct, Upside = 100¢ minus Entry.</p>
            <ExampleBox>
              Entry 43¢ → Upside <span className="text-[#3ddc84]">+57¢</span> (you risk 43¢ to potentially gain 57¢)<br />
              Entry 12¢ → Upside <span className="text-[#3ddc84]">+88¢</span> (you risk 12¢ to potentially gain 88¢)<br />
              Entry 85¢ → Upside <span className="text-[#3ddc84]">+15¢</span> (you risk 85¢ to potentially gain 15¢)
            </ExampleBox>
          </AccordionItem>

          <AccordionItem term="Score (0–100)">
            <p>A <strong className="text-[#e2e2f0]">quick-glance signal strength rating</strong> from 0 to 100. Higher is better. It's calculated from the edge — the bigger the difference between what the model thinks and what the market thinks, the higher the score.</p>
            <ExampleBox>
              Formula: Score = min(Edge × 200, 100)<br /><br />
              5% edge → Score <span className="text-[#6b6b8a]">10</span> (marginal)<br />
              15% edge → Score <span className="text-[#f5a623]">30</span> (moderate)<br />
              25% edge → Score <span className="text-[#3ddc84]">50</span> (solid)<br />
              50%+ edge → Score <span className="text-[#3ddc84]">100</span> (maximum)
            </ExampleBox>
            <Tip>A high score doesn't guarantee a win — it just means the model sees a large disagreement with the market. Always check Confidence too.</Tip>
          </AccordionItem>

          <AccordionItem term="Edge">
            <p>The <strong className="text-[#e2e2f0]">core metric</strong> — the difference between what our model predicts and what the market prices. A positive edge means our model thinks the outcome is more likely than the market does.</p>
            <p className="mt-2">Edge is what makes a bet potentially profitable long-term. Even if you lose individual bets, consistently betting with a positive edge should lead to profits over many bets (just like how casinos make money).</p>
            <ExampleBox>
              Our model: Brighton has a 65% chance of winning<br />
              Kalshi market: Brighton priced at 43% (43¢)<br />
              Edge = 65% - 43% = <span className="text-[#3ddc84]">+22%</span><br /><br />
              This means we think Brighton is significantly underpriced by the market.
            </ExampleBox>
            <Tip>The bigger the edge, the more the model disagrees with the market. But very large edges (30%+) with LOW confidence might mean the model lacks data rather than having found a genuine opportunity.</Tip>
          </AccordionItem>

          <AccordionItem term="LEAN vs STRONG Badges">
            <p>Quick visual labels that tell you how significant the edge is at a glance:</p>
            <p className="mt-2">
              <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-[#f5a623]/20 text-[#f5a623] mr-2">LEAN</span>
              <strong className="text-[#e2e2f0]">Edge under 20%</strong> — The model sees value, but it's a moderate disagreement with the market. These are more conservative picks.
            </p>
            <p className="mt-2">
              <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-[#e84040]/20 text-[#e84040] mr-2">STRONG</span>
              <strong className="text-[#e2e2f0]">Edge 20% or higher</strong> — The model sees significant mispricing. These are the model's highest-conviction picks, but make sure to check confidence level.
            </p>
            <Tip>STRONG doesn't mean "guaranteed win." It means the model thinks the market has this one wrong by a large margin. Always pair with confidence level to assess reliability.</Tip>
          </AccordionItem>

          <AccordionItem term="Model Comparison Box">
            <p>The dark inset box at the bottom of each card shows a <strong className="text-[#e2e2f0]">head-to-head comparison</strong> between what our model thinks and what the market thinks.</p>
            <ExampleBox>
              <span className="text-[#e2e2f0]">MODELS</span>: Poisson <span className="text-[#9b6dff]">65.4%</span><br />
              → Our Poisson model estimates a 65.4% chance of this outcome<br /><br />
              <span className="text-[#e2e2f0]">MARKET</span>: <span className="text-[#e2e2f0]">43.0%</span> <span className="text-[#3ddc84]">(+22.4% edge)</span> HIGH<br />
              → Kalshi is pricing it at 43%, giving us a 22.4% edge, and we have HIGH confidence in our data
            </ExampleBox>
            <p className="mt-2">Currently we only show one model (Poisson). As we add more models (Elo, XGBoost), they'll appear here too, along with a consensus estimate.</p>
          </AccordionItem>

          <AccordionItem term="Confidence Level">
            <p>How <strong className="text-[#e2e2f0]">trustworthy</strong> the prediction is, based on how much historical data we have for the teams involved.</p>
            <ExampleBox>
              <span className="text-[#3ddc84] font-semibold">HIGH</span> — 20+ matches for both teams in our database<br />
              → The model has seen these teams play many times. The prediction is well-grounded in data.<br /><br />
              <span className="text-[#f5a623] font-semibold">MEDIUM</span> — 10–19 matches for both teams<br />
              → Decent amount of data, but some uncertainty remains.<br /><br />
              <span className="text-[#e84040] font-semibold">LOW</span> — Fewer than 10 matches for one or both teams<br />
              → Limited data. The model is essentially guessing based on league averages. Treat with skepticism.
            </ExampleBox>
            <Tip>A 30% edge with HIGH confidence is much more trustworthy than a 40% edge with LOW confidence. Newly promoted teams or teams from smaller leagues will often have LOW confidence.</Tip>
          </AccordionItem>

          <AccordionItem term="$10 Bet Calculation (Footer)">
            <p>The footer shows what would happen if you placed a <strong className="text-[#e2e2f0]">$10 paper trade</strong> on this signal.</p>
            <ExampleBox>
              💡 $10 bet → win <span className="text-[#3ddc84]">+$13.26</span><br /><br />
              This means:<br />
              → You'd spend $10 to buy contracts at 43¢ each (~23 contracts)<br />
              → If the bet wins: you get back $23.26 total ($10 back + $13.26 profit)<br />
              → If the bet loses: you lose your $10
            </ExampleBox>
          </AccordionItem>
        </AccordionSection>

        {/* ── Section 3: Bet Types ── */}
        <AccordionSection
          title="Types of Bets"
          subtitle="The different ways you can bet on a soccer match"
          icon={Trophy}
          color="#f5a623"
        >
          <AccordionItem term="MONEYLINE (Match Winner)">
            <p>The simplest bet: <strong className="text-[#e2e2f0]">who wins the match?</strong> In soccer, this is a 3-way bet because draws are possible.</p>
            <ExampleBox>
              Chelsea vs Man Utd:<br />
              → Chelsea to win: <span className="text-[#9b6dff]">43¢</span> (43% implied probability)<br />
              → Draw: <span className="text-[#9b6dff]">27¢</span> (27% implied probability)<br />
              → Man Utd to win: <span className="text-[#9b6dff]">34¢</span> (34% implied probability)<br /><br />
              Note: the three prices might not add up to exactly 100¢ — the small difference is the market's built-in margin (called "overround" or "vig").
            </ExampleBox>
            <Tip>Moneyline bets are the easiest to understand and the most popular. They're a great place to start if you're new to betting.</Tip>
          </AccordionItem>

          <AccordionItem term="OVER_UNDER (Total Goals)">
            <p>A bet on whether the <strong className="text-[#e2e2f0]">total number of goals scored by both teams combined</strong> will be over or under a specific number. The ".5" ensures there's no push (tie).</p>
            <ExampleBox>
              Over 2.5 goals at <span className="text-[#9b6dff]">55¢</span>:<br />
              → <span className="text-[#3ddc84]">WIN</span> if final score has 3+ total goals (e.g., 2-1, 3-0, 2-2)<br />
              → <span className="text-[#e84040]">LOSE</span> if final score has 0, 1, or 2 total goals (e.g., 1-0, 0-0, 1-1)<br /><br />
              Available lines on Kalshi:<br />
              Over 1.5 goals → wins if 2+ goals total (very likely, so priced high ~80¢)<br />
              Over 2.5 goals → wins if 3+ goals total (moderate, ~55¢)<br />
              Over 3.5 goals → wins if 4+ goals total (less likely, ~30¢)<br />
              Over 4.5 goals → wins if 5+ goals total (unlikely, ~15¢)
            </ExampleBox>
            <Tip>Over/Under bets are popular because you don't need to pick a winner — you just need to predict whether the match will be high-scoring or low-scoring. Great for matches between two attacking teams.</Tip>
          </AccordionItem>

          <AccordionItem term="SPREAD (Goal Margin)">
            <p>A bet on whether a team will <strong className="text-[#e2e2f0]">win by more than a specific number of goals</strong>. This is like a "handicap" — the favorite needs to win convincingly, not just scrape by.</p>
            <ExampleBox>
              "Bayern Munich wins by 2+ goals" at <span className="text-[#9b6dff]">30¢</span>:<br />
              → <span className="text-[#3ddc84]">WIN</span> if Bayern wins 2-0, 3-0, 3-1, 4-0, 4-1, 4-2, etc.<br />
              → <span className="text-[#e84040]">LOSE</span> if Bayern wins 1-0, draws, or loses<br /><br />
              "Bayern Munich wins by 3+ goals" at <span className="text-[#9b6dff]">13¢</span>:<br />
              → <span className="text-[#3ddc84]">WIN</span> if Bayern wins 3-0, 4-0, 4-1, 5-0, etc.<br />
              → <span className="text-[#e84040]">LOSE</span> otherwise
            </ExampleBox>
            <Tip>Spread bets offer higher payouts than moneyline when you think a strong team will dominate. But they're harder to win — a 1-0 victory for the favorite still loses a "wins by 2+" bet.</Tip>
          </AccordionItem>

          <AccordionItem term="BTTS (Both Teams to Score)">
            <p>A simple yes/no bet: will <strong className="text-[#e2e2f0]">both teams score at least one goal</strong> in the match?</p>
            <ExampleBox>
              BTTS Yes at <span className="text-[#9b6dff]">57¢</span>:<br />
              → <span className="text-[#3ddc84]">WIN</span> if score is 1-1, 2-1, 1-2, 2-2, 3-1, 1-3, etc.<br />
              → <span className="text-[#e84040]">LOSE</span> if score is 1-0, 0-1, 2-0, 0-2, 0-0, etc.<br /><br />
              BTTS No at <span className="text-[#9b6dff]">43¢</span>:<br />
              → Opposite of above — wins if either team fails to score
            </ExampleBox>
            <Tip>BTTS is great when you know both teams have strong attacks but aren't sure who'll win. It's one of the most popular bet types in soccer.</Tip>
          </AccordionItem>

          <AccordionItem term="FIRST_HALF (First Half Winner)">
            <p>Just like a moneyline bet, but it only counts <strong className="text-[#e2e2f0]">what happens in the first 45 minutes</strong>. The score at halftime determines the result.</p>
            <ExampleBox>
              Chelsea leads at halftime: <span className="text-[#9b6dff]">32¢</span><br />
              Draw at halftime: <span className="text-[#9b6dff]">43¢</span><br />
              Man Utd leads at halftime: <span className="text-[#9b6dff]">28¢</span><br /><br />
              Note: draws at halftime are very common (~40-45% of matches), so the draw price tends to be highest.
            </ExampleBox>
            <Tip>First-half bets resolve faster (you know the result by halftime), but they're harder to predict because teams often take time to settle into a match. Draws at HT are very common.</Tip>
          </AccordionItem>
        </AccordionSection>

        {/* ── Section 4: Performance Metrics ── */}
        <AccordionSection
          title="Performance Metrics"
          subtitle="How to read the Performance page and track your results"
          icon={TrendingUp}
          color="#3ddc84"
        >
          <AccordionItem term="Win Rate">
            <p>The <strong className="text-[#e2e2f0]">percentage of settled bets that won</strong>. Only counts trades with a final result (WIN or LOSE), not pending ones.</p>
            <ExampleBox>
              8 wins out of 20 settled trades → Win Rate = <span className="text-[#3ddc84]">40%</span><br /><br />
              <strong className="text-[#e2e2f0]">What's a good win rate?</strong><br />
              It depends on the odds! Betting on heavy favorites (80¢+ entry) should win often but profits little each time. Betting on underdogs (20¢ entry) wins less often but pays big when it does.<br /><br />
              A 40% win rate can be very profitable if you're consistently betting on underpriced underdogs.
            </ExampleBox>
            <Tip>Win rate alone doesn't tell you if you're profitable. A 30% win rate on longshots can make more money than an 80% win rate on heavy favorites. Always look at ROI alongside win rate.</Tip>
          </AccordionItem>

          <AccordionItem term="ROI (Return on Investment)">
            <p>Your <strong className="text-[#e2e2f0]">total profit or loss as a percentage of total money staked</strong>. This is the single most important metric for evaluating the model.</p>
            <ExampleBox>
              Total staked: $500 across 50 bets<br />
              Total profit: +$75<br />
              ROI = +75 / 500 = <span className="text-[#3ddc84]">+15%</span><br /><br />
              <strong className="text-[#e2e2f0]">Benchmarks:</strong><br />
              → <span className="text-[#3ddc84]">+5% to +15% ROI</span> = Very good (professional level)<br />
              → <span className="text-[#3ddc84]">+1% to +5% ROI</span> = Good (beating the market)<br />
              → <span className="text-[#f5a623]">0% ROI</span> = Breaking even<br />
              → <span className="text-[#e84040]">Negative ROI</span> = Losing money, model needs improvement
            </ExampleBox>
            <Tip>Even the best sports bettors in the world typically achieve 3-10% ROI long term. If the model shows much higher than that early on, wait for more trades to settle — small sample sizes can be misleading.</Tip>
          </AccordionItem>

          <AccordionItem term="Cumulative PnL (Profit & Loss Chart)">
            <p>A <strong className="text-[#e2e2f0]">running total of profit and loss over time</strong>, shown as a line chart. This is the best way to see the model's trajectory.</p>
            <ExampleBox>
              <strong className="text-[#e2e2f0]">How to read it:</strong><br />
              → Line going <span className="text-[#3ddc84]">UP</span> = making money<br />
              → Line going <span className="text-[#e84040]">DOWN</span> = losing money<br />
              → Line at <span className="text-[#e2e2f0]">$0</span> (the horizontal reference line) = breakeven<br /><br />
              <strong className="text-[#e2e2f0]">What to look for:</strong><br />
              → Steadily rising line = model is consistently finding profitable bets ✅<br />
              → Sharp drops followed by recovery = normal variance, model is resilient ✅<br />
              → Steadily declining line = model is not working, needs recalibration ⚠️<br />
              → Wild swings up and down = high variance, might need to be more selective ⚠️
            </ExampleBox>
          </AccordionItem>

          <AccordionItem term="Max Drawdown">
            <p>The <strong className="text-[#e2e2f0]">largest drop from a peak to a trough</strong> in your cumulative PnL. It measures the worst losing streak in dollar terms.</p>
            <ExampleBox>
              Your PnL timeline:<br />
              Start $0 → Up to +$50 → Drop to -$10 → Recover to +$30<br />
              Max Drawdown = $50 to -$10 = <span className="text-[#e84040]">-$60</span><br /><br />
              <strong className="text-[#e2e2f0]">Why it matters:</strong><br />
              Even profitable strategies have losing streaks. Drawdown tells you how bad the worst streak has been. If you were betting real money, could you stomach that loss without panicking?
            </ExampleBox>
            <Tip>A good rule of thumb: your max drawdown should be less than your total profit. If drawdown is bigger, the model might be too risky even if it's currently profitable.</Tip>
          </AccordionItem>

          <AccordionItem term="Win/Loss/Pending Breakdown">
            <p>A simple <strong className="text-[#e2e2f0]">count of how many trades are in each status</strong>:</p>
            <ExampleBox>
              <span className="text-[#3ddc84]">WIN</span> — The bet was correct, profit was logged<br />
              <span className="text-[#e84040]">LOSE</span> — The bet was incorrect, loss was logged<br />
              <span className="text-[#f5d623]">PENDING</span> — The match hasn't finished yet, result unknown
            </ExampleBox>
          </AccordionItem>
        </AccordionSection>

        {/* ── Section 5: Accuracy ── */}
        <AccordionSection
          title="Model Accuracy"
          subtitle="How to tell if the model's predictions are reliable"
          icon={Target}
          color="#e84040"
        >
          <AccordionItem term="Calibration Chart">
            <p>The <strong className="text-[#e2e2f0]">most important chart for evaluating a prediction model</strong>. It answers the question: "When the model says 40%, does the event actually happen about 40% of the time?"</p>
            <ExampleBox>
              <strong className="text-[#e2e2f0]">How to read it:</strong><br />
              → X-axis: what the model predicted (grouped into 10% buckets)<br />
              → Y-axis: what actually happened (actual win rate in that bucket)<br />
              → Diagonal line: perfect calibration<br /><br />
              <strong className="text-[#e2e2f0]">Interpretation:</strong><br />
              → <span className="text-[#3ddc84]">Points on or near the diagonal</span> = model is well-calibrated ✅<br />
              → <span className="text-[#f5a623]">Points above the diagonal</span> = model is under-confident (reality beats prediction) — might be missing value<br />
              → <span className="text-[#e84040]">Points below the diagonal</span> = model is over-confident (prediction beats reality) — model needs to tone down its estimates<br /><br />
              Example: If the "30-40%" bucket shows an actual win rate of 50%, the model is under-confident in that range — it should be more aggressive.
            </ExampleBox>
            <Tip>You need at least 50-100 settled trades before the calibration chart becomes meaningful. With fewer trades, random variance will make it look unreliable.</Tip>
          </AccordionItem>

          <AccordionItem term="Rolling Win Rate">
            <p>A <strong className="text-[#e2e2f0]">moving average of win rate over the last 10 trades</strong>. This shows whether the model's accuracy is improving, stable, or declining over time.</p>
            <ExampleBox>
              <strong className="text-[#e2e2f0]">How to read it:</strong><br />
              → <span className="text-[#3ddc84]">Trending upward</span> = model is getting better or found its groove ✅<br />
              → <span className="text-[#e2e2f0]">Flat line around 40-60%</span> = stable performance ✅<br />
              → <span className="text-[#e84040]">Trending downward</span> = model performance is degrading, may need recalibration ⚠️<br />
              → <span className="text-[#f5a623]">Wild oscillation</span> = high variance, need more data to smooth out
            </ExampleBox>
          </AccordionItem>
        </AccordionSection>

        {/* ── Section 6: How the Model Works ── */}
        <AccordionSection
          title="How the Model Works"
          subtitle="The math and data behind the predictions"
          icon={PieChart}
          color="#9b6dff"
        >
          <AccordionItem term="Poisson Goal Model">
            <p>The <strong className="text-[#e2e2f0]">core prediction engine</strong>. It uses a statistical distribution called the Poisson distribution to predict how many goals each team will score.</p>
            <p className="mt-2">The key insight: goals in soccer are relatively rare and random events, which means they follow a Poisson distribution almost perfectly. If we know the "expected goals" for each team, we can calculate the probability of every possible scoreline (0-0, 1-0, 0-1, 1-1, 2-0, etc.) and from those, derive all our bet type probabilities.</p>
            <ExampleBox>
              <strong className="text-[#e2e2f0]">Step by step:</strong><br />
              1. Calculate expected goals for home team (λ_home = 2.1)<br />
              2. Calculate expected goals for away team (λ_away = 0.9)<br />
              3. Compute probability of every scoreline: P(0-0), P(1-0), P(0-1), ..., P(5-5)<br />
              4. Sum up: P(Home Win) = all scorelines where home &gt; away = 66%<br />
              5. Sum up: P(Over 2.5) = all scorelines with 3+ total goals = 62%<br />
              6. And so on for every bet type
            </ExampleBox>
          </AccordionItem>

          <AccordionItem term="Team Strength Ratings (Attack & Defense)">
            <p>Each team gets four ratings, calculated from their historical match data:</p>
            <ExampleBox>
              <strong className="text-[#e2e2f0]">Attack Home</strong> = how many goals they score at home vs league average<br />
              <strong className="text-[#e2e2f0]">Attack Away</strong> = how many goals they score away vs league average<br />
              <strong className="text-[#e2e2f0]">Defense Home</strong> = how many goals they concede at home vs league average<br />
              <strong className="text-[#e2e2f0]">Defense Away</strong> = how many goals they concede away vs league average<br /><br />
              <strong className="text-[#e2e2f0]">Example:</strong><br />
              Arsenal attack_home = 1.8 (they score 80% more at home than average)<br />
              Fulham defense_away = 1.3 (they concede 30% more away than average)<br /><br />
              Arsenal's expected goals = league_avg_home_goals × 1.8 × 1.3 = high!
            </ExampleBox>
          </AccordionItem>

          <AccordionItem term="Historical Data & Calibration">
            <p>The model is trained on the <strong className="text-[#e2e2f0]">last 12 months of finished matches</strong> from:</p>
            <ExampleBox>
              → <strong className="text-[#e2e2f0]">Premier League (EPL)</strong>: ~380 matches, 22 teams<br />
              → <strong className="text-[#e2e2f0]">Bundesliga</strong>: ~307 matches, 20 teams<br />
              → <strong className="text-[#e2e2f0]">Champions League (UCL)</strong>: ~189 matches, 36 teams<br /><br />
              Total: ~875 matches<br />
              Data source: football-data.org (free tier)<br />
              Cache: refreshed every 24 hours
            </ExampleBox>
            <Tip>More historical data = better predictions. As the season progresses and we accumulate more match results, team strength ratings become more accurate.</Tip>
          </AccordionItem>

          <AccordionItem term="Why Doesn't the Model Cover More Leagues?">
            <p>Currently Kalshi only offers per-match betting markets for EPL, Bundesliga, and UCL. Other leagues like La Liga, Serie A, Ligue 1, and Brasileiro only have futures markets (league winner, top 4, relegation) — not individual match betting.</p>
            <p className="mt-2">As Kalshi expands their soccer match offerings to more leagues, we'll add them to the model.</p>
          </AccordionItem>
        </AccordionSection>

        {/* ── Section 7: Tips & Strategy ── */}
        <AccordionSection
          title="Tips for Beginners"
          subtitle="Practical advice if you're new to prediction markets and betting"
          icon={Lightbulb}
          color="#f5d623"
        >
          <AccordionItem term="Start with paper trading" defaultOpen={true}>
            <p>Don't bet real money until you've tracked the model's performance for at least <strong className="text-[#e2e2f0]">2-4 weeks</strong> and are satisfied with its accuracy. This dashboard does all the paper trading for you automatically.</p>
            <Tip>Think of it like test-driving a car before buying it. The Performance and Accuracy pages are your test drive results.</Tip>
          </AccordionItem>

          <AccordionItem term="Understand that losses are normal">
            <p>Even the best models lose individual bets. What matters is <strong className="text-[#e2e2f0]">long-term profitability across many bets</strong>, not any single result.</p>
            <ExampleBox>
              Imagine flipping a weighted coin that lands heads 60% of the time:<br />
              → You'll still get tails ~40% of the time<br />
              → You might even get 5 tails in a row (bad luck!)<br />
              → But over 100+ flips, you'll come out ahead<br /><br />
              Betting with an edge works the same way.
            </ExampleBox>
          </AccordionItem>

          <AccordionItem term="Prioritize HIGH confidence signals">
            <p>When starting out, <strong className="text-[#e2e2f0]">focus on signals with HIGH confidence</strong>. These have the most historical data and the most reliable predictions. As you gain experience, you can experiment with MEDIUM confidence signals.</p>
            <p className="mt-2">Be very cautious with LOW confidence signals — large edges with low confidence often reflect limited data rather than genuine opportunities.</p>
          </AccordionItem>

          <AccordionItem term="Diversify across bet types">
            <p>Don't put all your (paper) eggs in one basket. The model finds value across different bet types:</p>
            <ExampleBox>
              → <strong className="text-[#e2e2f0]">Moneyline</strong> bets are straightforward but very efficient (hard to find large edges)<br />
              → <strong className="text-[#e2e2f0]">Over/Under</strong> and <strong className="text-[#e2e2f0]">BTTS</strong> markets can have more consistent edges because fewer people analyze them<br />
              → <strong className="text-[#e2e2f0]">Spread</strong> bets offer higher payouts but are harder to predict<br />
              → <strong className="text-[#e2e2f0]">First Half</strong> bets are the most volatile and hardest to model
            </ExampleBox>
          </AccordionItem>

          <AccordionItem term="Check the calibration chart regularly">
            <p>The calibration chart tells you if the model is trustworthy. If it starts showing systematic over-confidence (predictions higher than reality), that's a sign the model needs recalibration.</p>
          </AccordionItem>

          <AccordionItem term="Never bet more than you can afford to lose">
            <p>This is the golden rule. Sports betting — even with a statistical edge — involves real risk. Markets can be wrong, models can have blind spots, and losing streaks happen.</p>
            <p className="mt-2 text-[#e84040] font-semibold">🚫 This dashboard is a research tool, not financial advice. Always gamble responsibly.</p>
          </AccordionItem>
        </AccordionSection>

      </div>

      {/* Footer */}
      <div className="mt-10 mb-4 text-center text-[10px] text-[#6b6b8a]">
        Football Intel · Calibrated Poisson Model · Data from{' '}
        <a href="https://football-data.org" target="_blank" rel="noopener noreferrer" className="text-[#9b6dff] hover:text-[#b48fff]">
          football-data.org
        </a>
        {' '}·{' '}
        <a href="https://kalshi.com" target="_blank" rel="noopener noreferrer" className="text-[#9b6dff] hover:text-[#b48fff]">
          Kalshi
        </a>
      </div>
    </div>
  )
}
