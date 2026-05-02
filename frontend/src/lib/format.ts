export function formatTimestamp(timestamp: number): string {
  if (!timestamp) {
    return "—";
  }

  const date = timestamp < 1_000_000_000_000 ? new Date(timestamp * 1000) : new Date(timestamp);
  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
    month: "short",
    day: "numeric",
  }).format(date);
}

export function formatShortTime(timestamp: number): string {
  if (!timestamp) {
    return "—";
  }

  const date = timestamp < 1_000_000_000_000 ? new Date(timestamp * 1000) : new Date(timestamp);
  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function formatHash(hash: string): string {
  if (!hash) {
    return "—";
  }

  return `${hash.slice(0, 8)}...${hash.slice(-6)}`;
}

export function formatEth(value: string): string {
  const numeric = Number.parseFloat(value || "0");
  if (Number.isNaN(numeric)) {
    return "0.000";
  }

  return numeric.toLocaleString("en-US", {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  });
}
