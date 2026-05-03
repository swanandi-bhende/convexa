"use client";

import { useCallback, useEffect, useState } from "react";

const DEMO_MODE_KEY = "convexa.demoMode";
const AUTO_REFRESH_KEY = "convexa.autoRefresh";

interface UiSettings {
  demoMode: boolean;
  autoRefresh: boolean;
  setDemoMode: (enabled: boolean) => void;
  setAutoRefresh: (enabled: boolean) => void;
}

function readBooleanSetting(key: string, fallback: boolean): boolean {
  if (typeof window === "undefined") {
    return fallback;
  }

  const raw = window.localStorage.getItem(key);
  if (raw === null) {
    return fallback;
  }

  return raw === "1";
}

export function useUiSettings(): UiSettings {
  const [demoMode, setDemoModeState] = useState(true);
  const [autoRefresh, setAutoRefreshState] = useState(true);

  useEffect(() => {
    setDemoModeState(readBooleanSetting(DEMO_MODE_KEY, true));
    setAutoRefreshState(readBooleanSetting(AUTO_REFRESH_KEY, true));
  }, []);

  const setDemoMode = useCallback((enabled: boolean) => {
    setDemoModeState(enabled);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(DEMO_MODE_KEY, enabled ? "1" : "0");
    }
  }, []);

  const setAutoRefresh = useCallback((enabled: boolean) => {
    setAutoRefreshState(enabled);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(AUTO_REFRESH_KEY, enabled ? "1" : "0");
    }
  }, []);

  return {
    demoMode,
    autoRefresh,
    setDemoMode,
    setAutoRefresh,
  };
}
