"use client";

import React, { useEffect, useMemo, useState } from "react";
import { formatEther, parseEther } from "viem";
import { useAccount, useConnect, useDisconnect, useReadContract, useWaitForTransactionReceipt, useWriteContract } from "wagmi";
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
  const { address, isConnected } = useAccount();
  const { connect, connectors, isPending: isConnecting } = useConnect();
  const { disconnect } = useDisconnect();
  const { writeContractAsync, isPending: isWriting } = useWriteContract();
  const [selectedSide, setSelectedSide] = useState<StakeSide>("bull");
  const [amount, setAmount] = useState("0.05");
  const [pendingHash, setPendingHash] = useState<`0x${string}` | undefined>();
  const [submittedDeposit, setSubmittedDeposit] = useState<{ hash: `0x${string}`; side: StakeSide; amountWei: bigint } | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const bullShare = stakeShare(state.bullStakeTotal, state.bearStakeTotal);

  const stakeInfoQuery = useReadContract({
    address: CONTRACT_ADDRESSES.escrow,
    abi: DEBATE_ESCROW_ABI,
    functionName: "getStakeInfo",
    query: {
      refetchInterval: 15000,
    },
  });

  const userStakeQuery = useReadContract({
    address: CONTRACT_ADDRESSES.escrow,
    abi: DEBATE_ESCROW_ABI,
    functionName: "getUserStake",
    args: address ? [address] : undefined,
    query: {
      enabled: Boolean(address),
      refetchInterval: 15000,
    },
  });

  const waitingForReceipt = useWaitForTransactionReceipt({
    hash: pendingHash,
    query: {
      enabled: Boolean(pendingHash),
    },
  });

  const stakeInfo = stakeInfoQuery.data as readonly [bigint, bigint, boolean] | undefined;
  const userStake = userStakeQuery.data as readonly [bigint, bigint] | undefined;

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
    if (!waitingForReceipt.isSuccess || !pendingHash || !submittedDeposit) {
      return;
    }

    const sideLabel = submittedDeposit.side === "bull" ? "Bull" : "Bear";
    const timestamp = Date.now();

    dispatch({
      type: "DEPOSIT_MADE",
      payload: {
        depositor: address ?? "0x0000000000000000000000000000000000000000",
        side: submittedDeposit.side,
        amount: submittedDeposit.amountWei,
        hash: pendingHash,
        timestamp,
      },
    });
    dispatch({
      type: "TRANSACTION_CONFIRMED",
      payload: {
        hash: pendingHash,
        type: "deposit",
        timestamp,
        label: `${sideLabel} deposit confirmed`,
      },
    });

    setToast(`${sideLabel} deposit confirmed at ${formatTimestamp(timestamp)}`);
    setPendingHash(undefined);
    setSubmittedDeposit(null);
  }, [dispatch, pendingHash, submittedDeposit, waitingForReceipt.isSuccess]);

  useEffect(() => {
    if (!toast) {
      return;
    }

    const timeout = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  async function handleDeposit() {
    if (!isConnected) {
      setToast("Connect a wallet before depositing.");
      return;
    }

    if (!amount || Number.parseFloat(amount) <= 0) {
      setToast("Enter a valid deposit amount.");
      return;
    }

    try {
      const amountWei = parseEther(amount);
      const hash = await writeContractAsync({
        address: CONTRACT_ADDRESSES.escrow,
        abi: DEBATE_ESCROW_ABI,
        functionName: "deposit",
        args: [selectedSide === "bull" ? 0 : 1],
        value: amountWei,
      });

      setPendingHash(hash);
      setSubmittedDeposit({ hash, side: selectedSide, amountWei });
      setToast(`Transaction submitted for ${selectedSide === "bull" ? "Bull" : "Bear"}. Waiting for confirmation.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to submit deposit.";
      setToast(message);
    }
  }

  const isBusy = isConnecting || isWriting || waitingForReceipt.isLoading;

  return (
    <section className="glass-card-strong rounded-[28px] p-5 shadow-[0_24px_70px_rgba(0,0,0,0.35)] sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-white/40">Stake panel</p>
          <h3 className="mt-2 font-display text-4xl text-white">Capital position</h3>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/70">
          <span className={`h-2.5 w-2.5 rounded-full ${isConnected ? "bg-emerald-400" : "bg-amber-300"}`} />
          {isConnected ? shortAddress(address ?? "") : "Wallet disconnected"}
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-4">
          <div className="rounded-[22px] border border-emerald-400/12 bg-emerald-400/6 p-4">
            <div className="flex items-center justify-between text-sm text-white/70">
              <span>Bull stake</span>
              <span className="font-mono text-emerald-100">{state.bullStakeTotal} ETH</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/6">
              <div className="h-full rounded-full bg-linear-to-r from-emerald-500 to-emerald-300" style={{ width: `${bullShare}%` }} />
            </div>
          </div>

          <div className="rounded-[22px] border border-rose-400/12 bg-rose-400/6 p-4">
            <div className="flex items-center justify-between text-sm text-white/70">
              <span>Bear stake</span>
              <span className="font-mono text-rose-100">{state.bearStakeTotal} ETH</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/6">
              <div className="h-full rounded-full bg-linear-to-r from-rose-500 to-rose-300" style={{ width: `${100 - bullShare}%` }} />
            </div>
          </div>

          <div className="rounded-[24px] border border-white/8 bg-white/5 p-4 text-sm text-white/70">
            <div className="flex items-center justify-between">
              <span>Debate status</span>
              <span className={state.debateActive ? "text-emerald-200" : "text-amber-200"}>{state.debateActive ? "active" : "settled"}</span>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <span>Current round</span>
              <span className="font-mono text-white">{state.currentRound || 0}</span>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <span>Connection</span>
              <span className="font-mono text-white">{state.connectionStatus}</span>
            </div>
          </div>
        </div>

        <div className="rounded-[26px] border border-white/10 bg-surface/90 p-4 shadow-[0_12px_40px_rgba(0,0,0,0.24)]">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-white/35">Deposit</p>
              <h4 className="mt-1 font-display text-2xl text-white">Commit ETH to a side</h4>
            </div>
            {isConnected ? (
              <button className="rounded-full border border-white/10 px-3 py-2 text-xs text-white/70 transition hover:border-white/20 hover:text-white" onClick={() => disconnect()}>
                Disconnect
              </button>
            ) : null}
          </div>

          <div className="mt-5 grid gap-3">
            <div className="grid grid-cols-2 gap-2 rounded-[18px] border border-white/8 bg-white/5 p-2">
              {(["bull", "bear"] as StakeSide[]).map((side) => {
                const active = selectedSide === side;
                return (
                  <button
                    key={side}
                    className={`rounded-[14px] px-3 py-3 text-sm font-medium transition ${active ? "bg-white text-slate-950" : "text-white/70 hover:bg-white/6 hover:text-white"}`}
                    onClick={() => setSelectedSide(side)}
                  >
                    {side === "bull" ? "Bull" : "Bear"}
                  </button>
                );
              })}
            </div>

            <label className="grid gap-2">
              <span className="text-xs uppercase tracking-[0.28em] text-white/35">Amount in ETH</span>
              <input
                className="rounded-[18px] border border-white/10 bg-white/5 px-4 py-3 font-mono text-lg text-white outline-none transition placeholder:text-white/25 focus:border-white/25"
                inputMode="decimal"
                placeholder="0.05"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
              />
            </label>

            <div className="grid gap-3 rounded-[18px] border border-white/8 bg-white/5 p-4 text-sm text-white/70">
              <div className="flex items-center justify-between">
                <span>Your Bull stake</span>
                <span className="font-mono text-white">{personalBullStake} ETH</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Your Bear stake</span>
                <span className="font-mono text-white">{personalBearStake} ETH</span>
              </div>
            </div>

            {toast ? (
              <div className="rounded-[18px] border border-white/10 bg-white/5 px-4 py-3 text-sm text-white/75">{toast}</div>
            ) : null}

            {!isConnected ? (
              <button
                className="inline-flex items-center justify-center rounded-[18px] bg-white px-4 py-3 font-medium text-slate-950 transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={connectors.length === 0 || isConnecting}
                onClick={() => connect({ connector: connectors[0] })}
              >
                {isConnecting ? "Connecting..." : connectors.length ? "Connect wallet" : "No wallet connector"}
              </button>
            ) : (
              <button
                className="inline-flex items-center justify-center gap-2 rounded-[18px] bg-linear-to-r from-amber-200 to-amber-100 px-4 py-3 font-semibold text-slate-950 transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isBusy}
                onClick={handleDeposit}
              >
                {isWriting || waitingForReceipt.isLoading ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-950/30 border-t-slate-950" />
                    {waitingForReceipt.isLoading ? "Confirming deposit" : "Submitting deposit"}
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