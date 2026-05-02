"use client";

import React, { useEffect, useMemo, useState } from "react";
import { formatEther, parseEther, encodeFunctionData } from "viem";
import { CONTRACT_ADDRESSES, DEBATE_ESCROW_ABI } from "@/lib/contracts";
import { formatTimestamp } from "@/lib/format";
import { useDebateStore } from "@/store/debateStore";

type StakeSide = "bull" | "bear";

function stakeShare(bull: string, bear: string): number {
  const bullValue = Number.parseFloat(bull || "0");
  const bearValue = Number.parseFloat(bear || "0");
  const total = bullValue + bearValue;

  if (!total) {
    return 50;
  }

  return (bullValue / total) * 100;
}

function shortAddress(address: string): string {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function formatEthAmount(value: bigint | undefined): string {
  if (value === undefined) {
    return "0.000";
  }

  return Number.parseFloat(formatEther(value)).toFixed(3);
}

export function StakePanel() {
  const { state, dispatch } = useDebateStore();
  const [address, setAddress] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isWriting, setIsWriting] = useState(false);
  const [selectedSide, setSelectedSide] = useState<StakeSide>("bull");
  const [amount, setAmount] = useState("0.05");
  const [pendingHash, setPendingHash] = useState<`0x${string}` | undefined>();
  const [submittedDeposit, setSubmittedDeposit] = useState<{ hash: `0x${string}`; side: StakeSide; amountWei: bigint } | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const bullShare = stakeShare(state.bullStakeTotal, state.bearStakeTotal);

  const stakeInfo = undefined as unknown as readonly [bigint, bigint, boolean] | undefined;
  const userStake = undefined as unknown as readonly [bigint, bigint] | undefined;

  const personalBullStake = useMemo(() => formatEthAmount(userStake?.[0]), [userStake]);
  const personalBearStake = useMemo(() => formatEthAmount(userStake?.[1]), [userStake]);

  useEffect(() => {
    if (!stakeInfo) {
      return;
    }

    dispatch({
      type: "STAKE_TOTALS_REFRESHED",
      payload: {
        bullStakeTotal: Number.parseFloat(formatEther(stakeInfo[0])).toFixed(3),
        bearStakeTotal: Number.parseFloat(formatEther(stakeInfo[1])).toFixed(3),
      },
    });
  }, [dispatch, stakeInfo]);

  useEffect(() => {
    // detect existing wallet connection
    if (typeof window === "undefined" || !(window as any).ethereum) return;

    (async () => {
      try {
        const accounts: string[] = await (window as any).ethereum.request({ method: "eth_accounts" });
        if (accounts && accounts.length) {
          setAddress(accounts[0]);
          setIsConnected(true);
          dispatch({ type: "CONNECTION_STATUS_CHANGED", payload: "live" });
        } else {
          dispatch({ type: "CONNECTION_STATUS_CHANGED", payload: "disconnected" });
        }
      } catch {
        dispatch({ type: "CONNECTION_STATUS_CHANGED", payload: "disconnected" });
      }
    })();
  }, [dispatch]);

  // pendingHash is polled inside handleDeposit; no external wait hook is used.

  useEffect(() => {
    if (!toast) {
      return;
    }

    const timeout = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  async function handleDeposit() {
    if (!isConnected || !address) {
      setToast("Connect a wallet before depositing.");
      return;
    }

    if (!amount || Number.parseFloat(amount) <= 0) {
      setToast("Enter a valid deposit amount.");
      return;
    }

    if (!(window as any).ethereum) {
      setToast("No injected wallet detected.");
      return;
    }

    try {
      setIsWriting(true);
      const amountWei = parseEther(amount);
      const data = encodeFunctionData({ abi: DEBATE_ESCROW_ABI as any, functionName: "deposit", args: [selectedSide === "bull" ? 0 : 1] });

      const txParams = {
        to: CONTRACT_ADDRESSES.escrow,
        from: address,
        value: `0x${amountWei.toString(16)}`,
        data,
      } as Record<string, unknown>;

      // send transaction via injected provider
      const hash: string = await (window as any).ethereum.request({ method: "eth_sendTransaction", params: [txParams] });

      setPendingHash(hash as `0x${string}`);
      setSubmittedDeposit({ hash: hash as `0x${string}`, side: selectedSide, amountWei });
      setToast(`Transaction submitted for ${selectedSide === "bull" ? "Bull" : "Bear"}. Waiting for confirmation.`);

      // poll for receipt
      const interval = window.setInterval(async () => {
        try {
          const receipt = await (window as any).ethereum.request({ method: "eth_getTransactionReceipt", params: [hash] });
          if (receipt && receipt.blockNumber) {
            window.clearInterval(interval);
            const timestamp = Date.now();

            dispatch({
              type: "DEPOSIT_MADE",
              payload: {
                depositor: (address ?? "0x0000000000000000000000000000000000000000") as `0x${string}`,
                side: selectedSide,
                amount: submittedDeposit?.amountWei ?? amountWei,
                hash,
                timestamp,
              },
            });

            dispatch({
              type: "TRANSACTION_CONFIRMED",
              payload: {
                hash,
                type: "deposit",
                timestamp,
                label: `${selectedSide === "bull" ? "Bull" : "Bear"} deposit confirmed`,
              },
            });

            setToast(`${selectedSide === "bull" ? "Bull" : "Bear"} deposit confirmed at ${formatTimestamp(timestamp)}`);
            setPendingHash(undefined);
            setSubmittedDeposit(null);
            setIsWriting(false);
          }
        } catch {
          // ignore and continue polling
        }
      }, 2000);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to submit deposit.";
      setToast(message);
      setIsWriting(false);
    }
  }

  async function connectWallet() {
    if (!(window as any).ethereum) {
      setToast("No wallet found in the browser.");
      return;
    }

    try {
      setIsConnecting(true);
      const accounts: string[] = await (window as any).ethereum.request({ method: "eth_requestAccounts" });
      if (accounts && accounts.length) {
        setAddress(accounts[0]);
        setIsConnected(true);
        dispatch({ type: "CONNECTION_STATUS_CHANGED", payload: "live" });
      }
    } catch (err) {
      // user rejected or other
    } finally {
      setIsConnecting(false);
    }
  }

  function disconnect() {
    setAddress(null);
    setIsConnected(false);
    dispatch({ type: "CONNECTION_STATUS_CHANGED", payload: "disconnected" });
  }

  const isConfirming = Boolean(pendingHash);
  const isBusy = isConnecting || isWriting || isConfirming;

  return (
    <section className="glass-card-strong min-w-0 overflow-hidden rounded-[28px] p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-on-surface-variant">Stake panel</p>
          <h3 className="mt-2 font-display text-3xl text-on-surface sm:text-4xl">Capital position</h3>
        </div>
        <div className="flex items-center gap-2 rounded-full bg-surface-container-low px-3 py-2 text-xs text-on-surface">
          <span className={`h-2.5 w-2.5 rounded-full ${isConnected ? "bg-emerald-500" : "bg-amber-400"}`} />
          {isConnected ? shortAddress(address ?? "") : "Wallet disconnected"}
        </div>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-4">
          <div className="rounded-[22px] bg-surface p-4">
            <div className="flex items-center justify-between text-sm text-slate-600">
              <span>Bull stake</span>
              <span className="font-mono text-on-surface">{state.bullStakeTotal} ETH</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-surface-container-low">
              <div className="h-full rounded-full editorial-gradient" style={{ width: `${bullShare}%` }} />
            </div>
          </div>
          <div className="rounded-[22px] bg-surface p-4">
            <div className="flex items-center justify-between text-sm text-slate-600">
              <span>Bear stake</span>
              <span className="font-mono text-on-surface">{state.bearStakeTotal} ETH</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-surface-container-low">
              <div className="h-full rounded-full" style={{ width: `${100 - bullShare}%`, background: 'linear-gradient(135deg, rgba(141,72,97,0.9) 0%, rgba(109,87,81,0.9) 100%)' }} />
            </div>
          </div>

          <div className="rounded-[24px] bg-surface p-4 text-sm text-on-surface-variant">
            <div className="flex items-center justify-between">
              <span>Debate status</span>
              <span className={state.debateActive ? "text-emerald-700" : "text-amber-700"}>{state.debateActive ? "active" : "settled"}</span>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <span>Current round</span>
              <span className="font-mono text-on-surface">{state.currentRound || 0}</span>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <span>Connection</span>
              <span className="font-mono text-on-surface">{state.connectionStatus}</span>
            </div>
          </div>
        </div>

        <div className="min-w-0 rounded-[26px] bg-surface p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Deposit</p>
              <h4 className="mt-1 font-display text-2xl text-slate-900">Commit ETH to a side</h4>
            </div>
            {isConnected ? (
              <button className="rounded-full bg-surface-container-low px-3 py-2 text-xs text-on-surface transition" onClick={() => disconnect()}>
                Disconnect
              </button>
            ) : null}
          </div>

          <div className="mt-5 grid gap-3">
            <div className="grid grid-cols-2 gap-2 rounded-[18px] bg-surface-container-low p-2">
              {(["bull", "bear"] as StakeSide[]).map((side) => {
                const active = selectedSide === side;
                return (
                  <button
                    key={side}
                        className={`rounded-[14px] px-3 py-3 text-sm font-medium transition ${active ? "bg-surface text-on-surface shadow-sm" : "text-on-surface-variant hover:bg-surface"}`}
                    onClick={() => setSelectedSide(side)}
                  >
                    {side === "bull" ? "Bull" : "Bear"}
                  </button>
                );
              })}
            </div>

            <label className="grid gap-2">
              <span className="text-xs uppercase tracking-[0.28em] text-slate-500">Amount in ETH</span>
              <input
                className="rounded-[18px] bg-surface px-4 py-3 font-mono text-lg text-on-surface outline-none transition placeholder:text-on-surface-variant focus:ring-0"
                inputMode="decimal"
                placeholder="0.05"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
              />
            </label>

            <div className="grid gap-3 rounded-[18px] bg-surface-container-low p-4 text-sm text-on-surface-variant">
              <div className="flex items-center justify-between">
                <span>Your Bull stake</span>
                <span className="font-mono text-slate-900">{personalBullStake} ETH</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Your Bear stake</span>
                <span className="font-mono text-slate-900">{personalBearStake} ETH</span>
              </div>
            </div>

            {toast ? (
              <div className="rounded-[18px] bg-surface px-4 py-3 text-sm text-on-surface-variant">{toast}</div>
            ) : null}

            {!isConnected ? (
              <button
                className="inline-flex items-center justify-center rounded-[18px] editorial-gradient px-4 py-3 font-medium text-on-primary transition disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isConnecting}
                onClick={() => connectWallet()}
              >
                {isConnecting ? "Connecting..." : "Connect wallet"}
              </button>
            ) : (
              <button
                className="inline-flex items-center justify-center gap-2 rounded-[18px] editorial-gradient px-4 py-3 font-semibold text-on-primary transition disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isBusy}
                onClick={handleDeposit}
              >
                {isWriting || isConfirming ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-on-primary/30 border-t-on-primary" />
                    {isConfirming ? "Confirming deposit" : "Submitting deposit"}
                  </span>
                ) : (
                  `Deposit to ${selectedSide === "bull" ? "Bull" : "Bear"}`
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}