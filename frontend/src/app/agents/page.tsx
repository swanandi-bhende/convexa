import { AgentLeaderboard } from "@/components/AgentLeaderboard";
import { AgentStats } from "@/components/AgentStats";

const leaderboardRows = [
  { name: "Bull Core v2", side: "Bull" as const, accuracy: 72.4, wins: 124, avgConfidence: 76.1 },
  { name: "Bear Sentinel v1", side: "Bear" as const, accuracy: 69.8, wins: 109, avgConfidence: 73.5 },
  { name: "Bull Momentum v1", side: "Bull" as const, accuracy: 66.2, wins: 95, avgConfidence: 71.2 },
  { name: "Bear Risk Lens", side: "Bear" as const, accuracy: 64.9, wins: 88, avgConfidence: 69.7 },
];

const trendData = [
  { round: 1, bullAccuracy: 63, bearAccuracy: 58 },
  { round: 2, bullAccuracy: 65, bearAccuracy: 61 },
  { round: 3, bullAccuracy: 68, bearAccuracy: 64 },
  { round: 4, bullAccuracy: 70, bearAccuracy: 66 },
  { round: 5, bullAccuracy: 72, bearAccuracy: 68 },
  { round: 6, bullAccuracy: 74, bearAccuracy: 69 },
];

import { MegaBreadcrumb } from "@/components/MegaBreadcrumb";

export default function AgentsPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-24 pb-32 slide-up-fade">
      <MegaBreadcrumb />

      <section className="relative">
        <h1 className="display-lg text-on-surface mb-8">The AI Agents</h1>
        <p className="body-lg text-on-surface-variant max-w-3xl border-l-2 border-outline-variant pl-6 ml-4">
          Convexa operates via three distinct AI instances running on specialized <strong>Gensyn AXL nodes</strong>. 
          Each agent executes a Python-based reasoning loop, polling the Orchestrator for current market state 
          and emitting signed arguments back to the consensus engine.
        </p>
      </section>

      <section className="space-y-16">
        {/* Bull Agent Block */}
        <div className="tonal-card p-12 sm:p-16 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-64 h-full bg-bull-500/5 -skew-x-12 transform translate-x-12 group-hover:translate-x-0 transition-transform duration-700" />
          <div className="grid md:grid-cols-12 gap-12 relative z-10">
            <div className="md:col-span-4">
              <h2 className="headline-md text-bull-500 mb-2">Bull Agent</h2>
              <div className="label-md text-on-surface-variant flex items-center gap-2 mb-6">
                <span className="w-2 h-2 rounded-full bg-bull-500" />
                Port 8002 • AXL Node
              </div>
            </div>
            <div className="md:col-span-8 space-y-6 body-lg text-on-surface-variant">
              <p>
                The Bull Agent is configured with an aggressive, momentum-seeking prompt strategy (`bull_agent.py`). It specifically weights <strong>breakout patterns, positive funding rates, and high accumulation volume</strong> heavily in its context window.
              </p>
              <div className="bg-surface p-6 font-mono text-sm text-bull-500/80 mt-4 border-l-4 border-bull-500/30">
                &gt; Searching for resistance flips...<br/>
                &gt; Analyzing order block accumulation...<br/>
                &gt; Generating long thesis...
              </div>
            </div>
          </div>
        </div>

        {/* Bear Agent Block */}
        <div className="tonal-card p-12 sm:p-16 relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-64 h-full bg-bear-500/5 skew-x-12 transform -translate-x-12 group-hover:translate-x-0 transition-transform duration-700" />
          <div className="grid md:grid-cols-12 gap-12 relative z-10">
            <div className="md:col-span-4 md:order-last">
              <h2 className="headline-md text-bear-500 mb-2">Bear Agent</h2>
              <div className="label-md text-on-surface-variant flex items-center gap-2 mb-6">
                <span className="w-2 h-2 rounded-full bg-bear-500" />
                Port 8001 • AXL Node
              </div>
            </div>
            <div className="md:col-span-8 space-y-6 body-lg text-on-surface-variant">
              <p>
                Operating as the strict adversary, the Bear Agent (`bear_agent.py`) is designed to scrutinize the Bull's blind spots. It actively queries for <strong>bearish divergences, overbought RSI conditions, and macroeconomic risk factors</strong>.
              </p>
              <div className="bg-surface p-6 font-mono text-sm text-bear-500/80 mt-4 border-l-4 border-bear-500/30">
                &gt; Identifying liquidity sweeps...<br/>
                &gt; Calculating downside risk vector...<br/>
                &gt; Emitting short thesis...
              </div>
            </div>
          </div>
        </div>

        {/* Judge Agent Block */}
        <div className="tonal-card p-12 sm:p-16 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-64 h-full bg-tertiary/5 -skew-x-12 transform translate-x-12 group-hover:translate-x-0 transition-transform duration-700" />
          <div className="grid md:grid-cols-12 gap-12 relative z-10">
            <div className="md:col-span-4">
              <h2 className="headline-md text-tertiary mb-2">The Judge</h2>
              <div className="label-md text-on-surface-variant flex items-center gap-2 mb-6">
                <span className="w-2 h-2 rounded-full bg-tertiary" />
                Port 8003 • AXL Node
              </div>
            </div>
            <div className="md:col-span-8 space-y-6 body-lg text-on-surface-variant">
              <p>
                The Judge (`judge_agent.py`) is the consensus mechanism. It receives the signed JSON arguments from both the Bull and Bear. It evaluates the logical consistency, data accuracy, and persuasive weight of each argument to compute a final <strong>Conviction Score (0-100)</strong>.
              </p>
              <div className="bg-surface p-6 font-mono text-sm text-tertiary/80 mt-4 border-l-4 border-tertiary/30">
                &gt; Validating Bull argument...<br/>
                &gt; Cross-referencing Bear counterpoints...<br/>
                &gt; Verdict: Bull wins (Score: 68)...
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
