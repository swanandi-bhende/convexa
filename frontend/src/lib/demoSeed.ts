export type DemoDebate = {
  id: string;
  title: string;
  tokenPair: string;
  winner?: 'BULL' | 'BEAR' | 'TBD';
  rounds: number;
  createdAt: string;
};

const DEMO_DATA_KEY = 'convexa:demo-debates';

export const seedDemoDebates = () => {
  const now = Date.now();
  const sample: DemoDebate[] = [
    { id: 'd-001', title: 'ETH will outperform BTC this quarter', tokenPair: 'ETH/BTC', winner: 'TBD', rounds: 5, createdAt: new Date(now - 1000 * 60 * 60 * 24 * 3).toISOString() },
    { id: 'd-002', title: 'UNI will pump after protocol upgrade', tokenPair: 'UNI/USDC', winner: 'TBD', rounds: 3, createdAt: new Date(now - 1000 * 60 * 60 * 24 * 7).toISOString() },
    { id: 'd-003', title: 'ETH/USDC volatility will increase', tokenPair: 'ETH/USDC', winner: 'TBD', rounds: 4, createdAt: new Date(now - 1000 * 60 * 60 * 24 * 1).toISOString() },
  ];
  try {
    localStorage.setItem(DEMO_DATA_KEY, JSON.stringify(sample));
    return sample;
  } catch (e) {
    console.error('seedDemoDebates failed', e);
    return [] as DemoDebate[];
  }
};

export const clearDemoDebates = () => {
  try {
    localStorage.removeItem(DEMO_DATA_KEY);
  } catch {}
};

export const getDemoDebates = (): DemoDebate[] => {
  try {
    const raw = localStorage.getItem(DEMO_DATA_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as DemoDebate[];
  } catch {
    return [];
  }
};
