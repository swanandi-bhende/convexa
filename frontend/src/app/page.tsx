import Link from "next/link";
import { MetricsCard } from "@/components/MetricsCard";

export default function Home() {
  return (
    <div className="space-y-32 pb-32">
      {/* Hero Section - Asymmetrical */}
      <section className="relative pt-16 pb-20 sm:pt-24 sm:pb-32 lg:pl-12 lg:pr-24 slide-up-fade">
        <div className="absolute top-0 right-0 w-3/4 h-[120%] bg-gradient-to-bl from-[var(--surface-container-high)] to-transparent -z-10 rounded-l-full blur-3xl opacity-50" />
        
        <div className="max-w-4xl">
          <div className="inline-flex items-center gap-3 mb-10 slide-up-fade stagger-1">
            <span className="w-12 h-[1px] bg-secondary" />
            <span className="label-md text-secondary">The Digital Workforce</span>
          </div>
          
          <h1 className="display-lg text-on-surface slide-up-fade stagger-1">
            Autonomous market debate with <br/>
            <span className="text-gradient-primary">live conviction scoring.</span>
          </h1>
          
          <p className="mt-8 max-w-2xl body-lg text-on-surface-variant slide-up-fade stagger-2 ml-4 sm:ml-12 border-l-2 border-outline-variant pl-6">
            Watch specialized AI agents—Bull and Bear—argue in real time over market directions. Inspect the Judge's reasoning, and follow settlement signals in a fully transparent execution environment.
          </p>
          
          <div className="mt-16 flex flex-wrap items-center gap-8 slide-up-fade stagger-3 sm:ml-12">
            <Link href="/debate/demo-session" className="btn-primary px-8 py-4 label-md shadow-xl hover:-translate-y-1 transition-transform duration-300">
              Enter Live Debate
            </Link>
            <Link href="#architecture" className="label-md text-on-surface hover:text-secondary transition-colors relative group">
              How It Works
              <span className="absolute -bottom-2 left-0 w-0 h-[2px] bg-secondary transition-all duration-300 group-hover:w-full" />
            </Link>
          </div>
        </div>
      </section>

      {/* Metrics Section - Tonal Cards */}
      <section className="grid gap-8 md:grid-cols-3 slide-up-fade stagger-2 relative">
        <div className="absolute inset-y-0 -inset-x-10 bg-surface-container-low -z-10" />
        <div className="tonal-card p-10 py-12 text-center border-b-[3px] border-bull-500">
          <MetricsCard label="Active Debates" value="ETH/USDC" trend="Live Session" tone="bull" />
        </div>
        <div className="tonal-card p-10 py-12 text-center border-b-[3px] border-bull-500">
          <MetricsCard label="Total Stake Evaluated" value="215.0 ETH" trend="+12.4%" tone="bull" />
        </div>
        <div className="tonal-card p-10 py-12 text-center border-b-[3px] border-bull-500">
          <MetricsCard label="AI Consensus Accuracy" value="89.2%" trend="Last 30 rounds" tone="bull" />
        </div>
      </section>

      {/* Vision Section */}
      <section className="max-w-6xl mx-auto py-16 slide-up-fade">
        <div className="grid md:grid-cols-12 gap-16 items-start">
          <div className="md:col-span-5 md:pt-12">
            <h2 className="label-md text-tertiary mb-6">The Vision</h2>
            <h3 className="headline-md">Why We Built Convexa</h3>
            <div className="mt-8 space-y-6 body-lg text-on-surface-variant">
              <p>
                Traditional market analysis relies on single-threaded thinking or chaotic human sentiment. Convexa introduces an <strong className="text-on-surface font-semibold">adversarial AI framework</strong> designed to stress-test market thesis from both sides simultaneously.
              </p>
              <p>
                By pitting specialized, highly-contextualized AI agents against each other in structured, multi-round debates, we extract deeper insights, expose hidden risks, and generate highly reliable conviction scores.
              </p>
            </div>
          </div>
          
          <div className="md:col-span-7 bg-surface-container-highest p-12 sm:p-16 relative">
            <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 rounded-bl-full" />
            <h4 className="headline-md mb-8 flex items-center gap-4">
              <span className="text-tertiary">✦</span>
              The Analytical Edge
            </h4>
            <ul className="space-y-6 body-lg text-on-surface-variant">
              <li className="flex items-start gap-4">
                <span className="text-tertiary mt-1">01.</span> 
                <span><strong>Zero emotional bias.</strong> Pure data-driven analysis from multiple independent perspectives.</span>
              </li>
              <li className="flex items-start gap-4">
                <span className="text-tertiary mt-1">02.</span> 
                <span><strong>Continuous synthesis.</strong> 24/7 market evaluation without fatigue.</span>
              </li>
              <li className="flex items-start gap-4">
                <span className="text-tertiary mt-1">03.</span> 
                <span><strong>Transparent reasoning.</strong> Every decision is backed by a fully visible chain of logic.</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Architecture Section */}
      <section id="architecture" className="relative py-24 slide-up-fade">
        <div className="absolute inset-0 bg-surface-container-low -mx-8 sm:-mx-16 -z-10" />
        <div className="max-w-7xl mx-auto">
          <div className="mb-20 max-w-2xl">
            <h2 className="label-md text-tertiary mb-6">Architecture</h2>
            <h3 className="display-lg text-on-surface">The Digital Workforce</h3>
            <p className="mt-8 body-lg text-on-surface-variant">Four distinct AI components working in harmony on Gensyn AXL nodes to deliver actionable consensus. No black boxes, just pure algorithmic debate.</p>
          </div>

          <div className="grid md:grid-cols-2 gap-x-12 gap-y-16">
            {/* Bull Agent */}
            <div className="group relative pl-8">
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-bull-500/20 group-hover:bg-bull-500 transition-colors" />
              <h4 className="headline-md mb-4 text-bull-500">Bull Agent</h4>
              <p className="body-lg text-on-surface-variant">Runs on a dedicated AXL node (Port 8002). Relentlessly hunts for upward momentum, technical breakouts, and positive on-chain flow using specialized prompt strategies.</p>
            </div>

            {/* Bear Agent */}
            <div className="group relative pl-8">
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-bear-500/20 group-hover:bg-bear-500 transition-colors" />
              <h4 className="headline-md mb-4 text-bear-500">Bear Agent</h4>
              <p className="body-lg text-on-surface-variant">Runs independently (Port 8001). Focuses on resistance levels, volume divergence, macroeconomic headwinds, and potential dump risks to counter the Bull.</p>
            </div>

            {/* Judge Agent */}
            <div className="group relative pl-8">
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-tertiary/20 group-hover:bg-tertiary transition-colors" />
              <h4 className="headline-md mb-4">The Judge</h4>
              <p className="body-lg text-on-surface-variant">Evaluates the arguments from both sides (Port 8003). Scores them based on data validity, logic, and market relevance to determine the round winner and emit a conviction score.</p>
            </div>

            {/* Orchestrator */}
            <div className="group relative pl-8">
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary/20 group-hover:bg-primary transition-colors" />
              <h4 className="headline-md mb-4 text-primary">Orchestrator</h4>
              <p className="body-lg text-on-surface-variant">The Python-based central nervous system. Manages state transitions, triggers micro-settlements via Uniswap, and handles smart contract state updates on Unichain.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action */}
      <section className="text-center py-20 slide-up-fade">
        <h3 className="display-lg text-on-surface mb-12">Experience the Consensus</h3>
        <Link href="/debate/demo-session" className="btn-primary px-10 py-5 label-md shadow-2xl hover:shadow-[0_20px_40px_rgba(134,79,81,0.3)] hover:-translate-y-2 transition-all duration-300 inline-flex items-center gap-4">
          Open Demo Session 
          <span aria-hidden="true" className="text-lg">→</span>
        </Link>
      </section>
    </div>
  );
}
