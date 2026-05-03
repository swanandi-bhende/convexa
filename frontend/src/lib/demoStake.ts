export type StakeSide = "bull" | "bear";

export interface DemoStakeEvent {
  id: string;
  side: StakeSide;
  amount: number;
  status: "queued" | "applied";
  createdAt: number;
}

interface StakeStore {
  bull: number;
  bear: number;
  events: DemoStakeEvent[];
}

const STORAGE_KEY = "convexa.demoStakeStore";
const EVENT_NAME = "convexa:stake";

function safeParse(raw: string | null): StakeStore | null {
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as StakeStore;
  } catch {
    return null;
  }
}

function readStore(): StakeStore {
  if (typeof window === "undefined") {
    return { bull: 0, bear: 0, events: [] };
  }

  const parsed = safeParse(window.localStorage.getItem(STORAGE_KEY));
  if (!parsed) {
    return { bull: 0, bear: 0, events: [] };
  }

  return {
    bull: Number(parsed.bull || 0),
    bear: Number(parsed.bear || 0),
    events: Array.isArray(parsed.events) ? parsed.events.slice(0, 20) : [],
  };
}

function writeStore(store: StakeStore) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

function emitChange() {
  if (typeof window === "undefined") {
    return;
  }

  window.dispatchEvent(new CustomEvent(EVENT_NAME));
}

export function getDemoStakeStore(): StakeStore {
  return readStore();
}

export function queueDemoStake(side: StakeSide, amount: number): DemoStakeEvent {
  const now = Date.now();
  const event: DemoStakeEvent = {
    id: `stake-${now}`,
    side,
    amount,
    status: "queued",
    createdAt: now,
  };

  const current = readStore();
  const next: StakeStore = {
    ...current,
    events: [event, ...current.events].slice(0, 20),
  };

  writeStore(next);
  emitChange();

  return event;
}

export function markDemoStakeApplied(eventId: string): DemoStakeEvent | null {
  const current = readStore();
  const target = current.events.find((item) => item.id === eventId);
  if (!target || target.status === "applied") {
    return null;
  }

  const applied: DemoStakeEvent = {
    ...target,
    status: "applied",
  };

  const nextEvents = current.events.map((item) => (item.id === eventId ? applied : item));
  const next: StakeStore = {
    bull: current.bull + (applied.side === "bull" ? applied.amount : 0),
    bear: current.bear + (applied.side === "bear" ? applied.amount : 0),
    events: nextEvents,
  };

  writeStore(next);
  emitChange();

  return applied;
}

export function subscribeDemoStakeStore(onChange: (store: StakeStore) => void): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  const handle = () => {
    onChange(readStore());
  };

  window.addEventListener(EVENT_NAME, handle);
  window.addEventListener("storage", handle);

  return () => {
    window.removeEventListener(EVENT_NAME, handle);
    window.removeEventListener("storage", handle);
  };
}
