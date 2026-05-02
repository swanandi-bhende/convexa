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
    <section className="glass-card-strong min-w-0 overflow-hidden rounded-[28px] p-5 shadow-[0_24px_70px_rgba(60,48,36,0.08)] sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Stake panel</p>
          <h3 className="mt-2 font-display text-4xl text-slate-900">Capital position</h3>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">
          <span className={`h-2.5 w-2.5 rounded-full ${isConnected ? "bg-emerald-500" : "bg-amber-400"}`} />
          {isConnected ? shortAddress(address ?? "") : "Wallet disconnected"}
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-4">
          <div className="rounded-[22px] border border-emerald-200 bg-emerald-50 p-4">
            <div className="flex items-center justify-between text-sm text-slate-600">
              <span>Bull stake</span>
              <span className="font-mono text-emerald-700">{state.bullStakeTotal} ETH</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-emerald-100">
              <div className="h-full rounded-full bg-linear-to-r from-emerald-500 to-emerald-300" style={{ width: `${bullShare}%` }} />
            </div>
          </div>

          <div className="rounded-[22px] border border-rose-200 bg-rose-50 p-4">
            <div className="flex items-center justify-between text-sm text-slate-600">
              <span>Bear stake</span>
              <span className="font-mono text-rose-700">{state.bearStakeTotal} ETH</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-rose-100">
              <div className="h-full rounded-full bg-linear-to-r from-rose-500 to-rose-300" style={{ width: `${100 - bullShare}%` }} />
            </div>
          </div>

          <div className="rounded-[24px] border border-slate-200 bg-white p-4 text-sm text-slate-600 shadow-[0_10px_30px_rgba(60,48,36,0.05)]">
            <div className="flex items-center justify-between">
              <span>Debate status</span>
              <span className={state.debateActive ? "text-emerald-700" : "text-amber-700"}>{state.debateActive ? "active" : "settled"}</span>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <span>Current round</span>
              <span className="font-mono text-slate-900">{state.currentRound || 0}</span>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <span>Connection</span>
              <span className="font-mono text-slate-900">{state.connectionStatus}</span>
            </div>
          </div>
        </div>

        <div className="min-w-0 rounded-[26px] border border-slate-200 bg-white p-4 shadow-[0_12px_40px_rgba(60,48,36,0.06)]">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Deposit</p>
              <h4 className="mt-1 font-display text-2xl text-slate-900">Commit ETH to a side</h4>
            </div>
            {isConnected ? (
              <button className="rounded-full border border-slate-200 px-3 py-2 text-xs text-slate-600 transition hover:border-slate-300 hover:text-slate-900" onClick={() => disconnect()}>
                Disconnect
              </button>
            ) : null}
          </div>

          <div className="mt-5 grid gap-3">
            <div className="grid grid-cols-2 gap-2 rounded-[18px] border border-slate-200 bg-slate-50 p-2">
              {(["bull", "bear"] as StakeSide[]).map((side) => {
                const active = selectedSide === side;
                return (
                  <button
                    key={side}
                    className={`rounded-[14px] px-3 py-3 text-sm font-medium transition ${active ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:bg-white hover:text-slate-900"}`}
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
                className="rounded-[18px] border border-slate-200 bg-white px-4 py-3 font-mono text-lg text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-slate-300"
                inputMode="decimal"
                placeholder="0.05"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
              />
            </label>

            <div className="grid gap-3 rounded-[18px] border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
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
              <div className="rounded-[18px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">{toast}</div>
            ) : null}

            {!isConnected ? (
              <button
                className="inline-flex items-center justify-center rounded-[18px] bg-slate-900 px-4 py-3 font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isConnecting}
                onClick={() => connectWallet()}
              >
                {isConnecting ? "Connecting..." : "Connect wallet"}
              </button>
            ) : (
              <button
                className="inline-flex items-center justify-center gap-2 rounded-[18px] bg-linear-to-r from-amber-200 to-amber-100 px-4 py-3 font-semibold text-slate-900 transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isBusy}
                onClick={handleDeposit}
              >
                {isWriting || isConfirming ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-950/30 border-t-slate-950" />
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