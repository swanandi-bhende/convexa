const DEFAULT_ESCROW_ADDRESS = "0xBB7bD22Aa37E05979c3858540048e99bCa98CEF9" as const;
const DEFAULT_CONVICTION_ADDRESS = "0x1709ce3a1c4506F6889C797dde6Cb9e0950173ED" as const;
const DEFAULT_HTTP_URL = "https://unichain-sepolia.g.alchemy.com/v2/95NIC2Ppi1WoV9j-fkqh5";
const DEFAULT_WS_URL = "wss://unichain-sepolia.g.alchemy.com/v2/95NIC2Ppi1WoV9j-fkqh5";

function normalizeHttpUrl(wsUrl: string): string {
  if (wsUrl.startsWith("wss://")) {
    return `https://${wsUrl.slice(6)}`;
  }

  if (wsUrl.startsWith("ws://")) {
    return `http://${wsUrl.slice(5)}`;
  }

  return DEFAULT_HTTP_URL;
}

export const CONTRACT_ADDRESSES = {
  escrow: (process.env.NEXT_PUBLIC_ESCROW_ADDRESS || DEFAULT_ESCROW_ADDRESS) as `0x${string}`,
  conviction: (process.env.NEXT_PUBLIC_CONVICTION_ADDRESS || DEFAULT_CONVICTION_ADDRESS) as `0x${string}`,
};

const wsUrl = process.env.NEXT_PUBLIC_ALCHEMY_WS_URL || DEFAULT_WS_URL;

export const RPC_URLS = {
  http: process.env.NEXT_PUBLIC_ALCHEMY_HTTP_URL || process.env.NEXT_PUBLIC_ALCHEMY_RPC_URL || normalizeHttpUrl(wsUrl),
  ws: wsUrl,
};

export const CHAIN_ID = Number.parseInt(process.env.NEXT_PUBLIC_CHAIN_ID || "1301", 10);

export const CONVICTION_TRACKER_ABI = [
  {
    inputs: [],
    name: "getCurrentScores",
    outputs: [
      { name: "bullScore", type: "uint256" },
      { name: "bearScore", type: "uint256" },
      { name: "roundNumber", type: "uint256" },
      { name: "isActive", type: "bool" },
    ],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [],
    name: "getRoundHistory",
    outputs: [
      {
        components: [
          { name: "roundNumber", type: "uint256" },
          { name: "bullScore", type: "uint256" },
          { name: "bearScore", type: "uint256" },
          { name: "winner", type: "address" },
          { name: "timestamp", type: "uint256" },
        ],
        name: "roundHistory",
        type: "tuple[]",
      },
    ],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [{ name: "roundNumber", type: "uint256" }],
    name: "getRound",
    outputs: [
      {
        components: [
          { name: "roundNumber", type: "uint256" },
          { name: "bullScore", type: "uint256" },
          { name: "bearScore", type: "uint256" },
          { name: "winner", type: "address" },
          { name: "timestamp", type: "uint256" },
        ],
        name: "roundResult",
        type: "tuple",
      },
    ],
    stateMutability: "view",
    type: "function",
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true, name: "roundNumber", type: "uint256" },
      { indexed: false, name: "bullScore", type: "uint256" },
      { indexed: false, name: "bearScore", type: "uint256" },
      { indexed: false, name: "timestamp", type: "uint256" },
    ],
    name: "ConvictionUpdated",
    type: "event",
  },
  {
    anonymous: false,
    inputs: [
      { indexed: false, name: "winningSide", type: "string" },
      { indexed: false, name: "finalBullScore", type: "uint256" },
      { indexed: false, name: "finalBearScore", type: "uint256" },
      { indexed: false, name: "winningRound", type: "uint256" },
    ],
    name: "DebateWinnerDeclared",
    type: "event",
  },
] as const;

export const DEBATE_ESCROW_ABI = [
  {
    inputs: [],
    name: "getStakeInfo",
    outputs: [
      { name: "bullTotal", type: "uint256" },
      { name: "bearTotal", type: "uint256" },
      { name: "isDebateActive", type: "bool" },
    ],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [{ name: "user", type: "address" }],
    name: "getUserStake",
    outputs: [
      { name: "bullStake", type: "uint256" },
      { name: "bearStake", type: "uint256" },
    ],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [{ name: "side", type: "uint8" }],
    name: "deposit",
    outputs: [],
    stateMutability: "payable",
    type: "function",
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true, name: "user", type: "address" },
      { indexed: false, name: "side", type: "uint8" },
      { indexed: false, name: "amount", type: "uint256" },
    ],
    name: "Deposited",
    type: "event",
  },
  {
    anonymous: false,
    inputs: [
      { indexed: false, name: "startTime", type: "uint256" },
      { indexed: false, name: "endTime", type: "uint256" },
    ],
    name: "DebateStarted",
    type: "event",
  },
] as const;
