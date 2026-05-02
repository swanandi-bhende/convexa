'use client';

import { useEffect, useState } from 'react';

const DEMO_KEY = 'convexa:demo-mode';

export function useDemoMode() {
  const [enabled, setEnabled] = useState<boolean>(() => {
    try {
      const v = localStorage.getItem(DEMO_KEY);
      return v === '1';
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      if (enabled) localStorage.setItem(DEMO_KEY, '1');
      else localStorage.removeItem(DEMO_KEY);
    } catch {}
  }, [enabled]);

  return { enabled, setEnabled } as const;
}
