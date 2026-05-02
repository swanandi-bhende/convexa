"use client";

import React, { useState, useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { defineChain, http } from "viem";
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

// No wagmi provider: using lightweight injected-provider flows in components.

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  // No runtime wagmi hydration required.

  return (
    <QueryClientProvider client={queryClient}>
      <DebateProvider>{children}</DebateProvider>
    </QueryClientProvider>
  );
}
