"use client";

import React, { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { defineChain, http } from "viem";
import { WagmiProvider, createConfig } from "wagmi";
import dynamic from "next/dynamic";
import { DebateProvider } from "@/store/debateStore";
import { RPC_URLS, CHAIN_ID } from "@/lib/contracts";

const unichainSepolia = defineChain({
  id: CHAIN_ID,
  name: "Unichain Sepolia",
  nativeCurrency: { name: "Ether", symbol: "ETH", decimals: 18 },
  rpcUrls: {
    default: {
      http: [RPC_URLS.http],
      webSocket: [RPC_URLS.ws],
    },
  },
  blockExplorers: {
    default: {
      name: "Blockscout",
      url: "https://sepolia.unichain.org",
    },
  },
});

// Create a default config placeholder. We'll hydrate the real connectors on the client.
const wagmiConfig = createConfig({
  autoConnect: false,
  connectors: [],
  transports: {},
});

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  const [hydratedConfig, setHydratedConfig] = useState(wagmiConfig);

  useEffect(() => {
    let mounted = true;

    async function hydrate() {
      try {
        const { injected } = await import("wagmi/connectors/injected");
        if (!mounted) return;
        const cfg = createConfig({
          autoConnect: true,
          connectors: [injected()],
          transports: {
            [unichainSepolia.id]: http(RPC_URLS.http),
          },
        });

        setHydratedConfig(cfg);
      } catch {
        // fall back to client-only behavior
      }
    }

    void hydrate();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <WagmiProvider config={hydratedConfig}>
        <DebateProvider>{children}</DebateProvider>
      </WagmiProvider>
    </QueryClientProvider>
  );
}
