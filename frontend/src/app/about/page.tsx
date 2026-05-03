import Link from "next/link";

import { MegaBreadcrumb } from "@/components/MegaBreadcrumb";

export default function AboutPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-24 pb-32 slide-up-fade">
      <MegaBreadcrumb />

      <section className="max-w-4xl">
        <h1 className="display-lg text-on-surface mb-8">About Convexa</h1>
        <p className="body-lg text-on-surface-variant border-l-2 border-outline-variant pl-6 ml-4">
          Convexa is a decentralized, autonomous market analysis platform powered by the <strong>AI Digital Workforce</strong>. 
          By combining off-chain compute (Gensyn AXL nodes) with on-chain settlement (Unichain), we create a verifiable, 
          tamper-proof record of AI conviction.
        </p>
      </section>

      <section className="grid md:grid-cols-2 gap-16">
        <div className="tonal-card p-12 relative overflow-hidden group">
          <div className="absolute -right-16 -top-16 w-48 h-48 bg-primary/5 rounded-full group-hover:scale-150 transition-transform duration-700" />
          <h2 className="headline-md mb-6">Off-Chain Execution</h2>
          <div className="space-y-4 body-lg text-on-surface-variant relative z-10">
            <p>
              The heavy lifting of data fetching, natural language processing, and adversarial debate occurs off-chain.
            </p>
            <ul className="space-y-3 mt-4">
              <li className="flex items-start gap-3"><span className="text-secondary">▹</span> <strong>Orchestrator:</strong> Manages state and coordinates agents.</li>
              <li className="flex items-start gap-3"><span className="text-secondary">▹</span> <strong>Gensyn AXL Nodes:</strong> Provide the decentralized compute layer for the Bull, Bear, and Judge LLM prompts.</li>
            </ul>
          </div>
        </div>

        <div className="tonal-card p-12 relative overflow-hidden group">
          <div className="absolute -left-16 -bottom-16 w-48 h-48 bg-secondary/5 rounded-full group-hover:scale-150 transition-transform duration-700" />
          <h2 className="headline-md mb-6">On-Chain Settlement</h2>
          <div className="space-y-4 body-lg text-on-surface-variant relative z-10">
            <p>
              Once the Judge determines a Conviction Score, the Orchestrator commits this state to the Unichain network via the <code>ConvictionTracker</code> smart contract.
            </p>
            <ul className="space-y-3 mt-4">
              <li className="flex items-start gap-3"><span className="text-secondary">▹</span> <strong>ConvictionTracker:</strong> Emits verifiable score updates.</li>
              <li className="flex items-start gap-3"><span className="text-secondary">▹</span> <strong>Micro-Settlements:</strong> The Orchestrator automatically triggers Uniswap trades based on the Judge's verdict, creating a financial footprint of the AI's consensus.</li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
