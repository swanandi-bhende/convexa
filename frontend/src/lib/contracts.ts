// Contract ABIs and configuration
export const DEBATE_ESCROW_ABI = [
  {
    inputs: [{ name: 'side', type: 'uint8' }],
    name: 'deposit',
    outputs: [],
    stateMutability: 'payable',
    type: 'function',
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true, name: 'depositor', type: 'address' },
      { indexed: false, name: 'side', type: 'uint8' },
      { indexed: false, name: 'amount', type: 'uint256' },
    ],
    name: 'Deposited',
    type: 'event',
  },
] as const;

export const CONVICTION_TRACKER_ABI = [
  {
    inputs: [{ name: 'roundNumber', type: 'uint256' }],
    name: 'getRoundConviction',
    outputs: [
      { name: 'bullScore', type: 'uint256' },
      { name: 'bearScore', type: 'uint256' },
    ],
    stateMutability: 'view',
    type: 'function',
  },
  {
    anonymous: false,
    inputs: [
      { indexed: false, name: 'roundNumber', type: 'uint256' },
      { indexed: false, name: 'bullScore', type: 'uint256' },
      { indexed: false, name: 'bearScore', type: 'uint256' },
    ],
    name: 'ConvictionUpdated',
    type: 'event',
  },
] as const;

export const CONTRACT_ADDRESSES = {
  escrow: (process.env.NEXT_PUBLIC_ESCROW_ADDRESS || '0xBB7bD22Aa37E05979c3858540048e99bCa98CEF9') as `0x${string}`,
  conviction: (process.env.NEXT_PUBLIC_CONVICTION_ADDRESS || '0x1709ce3a1c4506F6889C797dde6Cb9e0950173ED') as `0x${string}`,
};

export const RPC_URLS = {
  http: process.env.NEXT_PUBLIC_ALCHEMY_RPC_URL || 'https://unichain-sepolia.g.alchemy.com/v2/95NIC2Ppi1WoV9j-fkqh5',
  ws: process.env.NEXT_PUBLIC_ALCHEMY_WS_URL || 'wss://unichain-sepolia.g.alchemy.com/v2/95NIC2Ppi1WoV9j-fkqh5',
};

export const CHAIN_ID = parseInt(process.env.NEXT_PUBLIC_CHAIN_ID || '1301', 10);
