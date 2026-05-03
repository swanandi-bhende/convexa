# Convexa Demo Test Flow

This runbook is for recording demos and for QA handoff. It covers both:
- Demo Mode: no live backend required, safe for stable recordings.
- Normal Mode: live API/websocket/on-chain connected flow.

## 1) Pre-Demo Checklist (2-3 minutes)

1. Open app URL and hard refresh once.
2. Open [Settings](../frontend/src/app/settings/page.tsx) in the UI.
3. Decide mode:
- Demo recording reliability: keep Demo Mode ON.
- Live system validation: set Demo Mode OFF.
4. Keep Auto-refresh ON unless you are explicitly testing no-refresh behavior.
5. Keep a wallet extension unlocked (MetaMask or Rabby) if wallet demo is included.

Pass criteria:
- App loads without blank screen.
- Navigation is clickable.
- No fatal error overlay.

## 2) Recommended Recording Plan

- Total recommended video length: 6 to 9 minutes.
- Demo Mode section: 3 to 4 minutes.
- Normal Mode section: 3 to 5 minutes.

## 3) Demo Mode Test Flow (Offline-Safe)

Set in Settings:
- Demo Mode: ON
- Auto-refresh: ON

### Step A: Home and Navigation (20-30s)

1. Go to Home.
2. Verify Quick Start path by clicking Watch Debate or Open Live Debate.

Expected:
- Route opens /debate/demo-session.
- Header and sidebar remain responsive.

### Step B: Debate Session Movement (45-75s)

1. Stay on /debate/demo-session.
2. Watch round, scores, argument text, and market values.

Wait guidance:
- First visible update: wait 6 to 12 seconds.
- Two updates for camera proof: wait 15 to 25 seconds total.

Expected:
- Round number changes over time.
- Bull/Bear score values change.
- Bull/Bear argument text updates.
- Conviction bar updates with score changes.
- WS badge may show Polling in demo mode (acceptable).

Fail signal:
- No value changes after 25 seconds with Auto-refresh ON.

### Step C: Wallet Connect UI (20-40s)

1. Click Connect Wallet in header.
2. Approve wallet prompt.

Wait guidance:
- Wallet prompt should appear in 3 to 8 seconds.
- Address pill updates within 1 to 3 seconds after approval.

Expected:
- Button changes from Connect Wallet to shortened address.
- If wrong chain, app requests switch/add chain.

### Step D: Stake Demo (20-30s)

1. Go to /stake.
2. Submit Bull 0.05 ETH, then Bear 0.1 ETH.

Expected:
- Message first shows queued, then applied.
- Stake Event Feed shows each action status progressing from queued -> applied.
- Settlement Status values change after each applied event:
- Escrow balance increases.
- Pending payouts reflects queued items.
- Returning to /debate/demo-session shows stake totals reflected in Bull/Bear metrics.

Wait guidance:
- Queue confirmation: immediate (0-1s).
- Applied state: about 3-5s after submit.

### Step E: Agents and History Filters (45-60s)

1. Go to /agents, type pair filter value, click Apply Filters.
2. Go to /history, search ETH/USDC or Bull.
3. Click a debate card in history.

Expected:
- Filter inputs accept values and page remains interactive.
- History detail panel updates after selecting a card.

## 4) Normal Mode Test Flow (Live Data)

Set in Settings:
- Demo Mode: OFF
- Auto-refresh: ON

### Step A: Initial API Load (15-30s)

1. Open /debate/demo-session.
2. Watch for skeleton loading to finish.

Expected:
- Debate cards and market snapshot render.
- No persistent red error panel.

Fail signal:
- Red error panel remains for more than 30 seconds.

### Step B: Live vs Polling Status (30-60s)

1. Observe connection indicator on debate header.

Wait guidance:
- WS Live indicator may appear within 5 to 20 seconds.
- If live feed becomes stale, UI should switch into Replay mode for demo continuity.

Expected:
- Green Live: websocket stream active.
- Amber Polling: backend polling fallback active.
- Blue Replay: stale-feed fallback is simulating round progression so the demo stays explainable.

Fail signal:
- Stuck on Polling for 30+ seconds with no transition to Live or Replay.

### Step C: Data Freshness Proof (60-90s)

1. Keep camera on round/scores/history.
2. Wait for at least one new update cycle.

Wait guidance:
- Polling refresh window is typically 8 to 12 seconds.
- If no fresh backend movement for 30 seconds, Replay mode should kick in.
- Use 45 seconds as max wait before calling the UI stale.

Expected:
- Round history list or score values update at least once.
- Bull/Bear argument text should change with round evolution (not fixed copy).

### Step D: Wallet Connect in Normal Mode (20-40s)

1. Click Connect Wallet.
2. Approve connect + network switch if prompted.

Expected:
- Connected address appears in header.
- No persistent wallet error message.

### Step E: Stake and Log Verification (45-75s)

1. Submit a demo stake amount from /stake.
2. Move to /history and /agents to verify app remains stable.

Expected:
- Stake action shows queued/confirmation UI feedback.
- No crash or frozen state when navigating.

Note:
- In current demo build, stake UI may be queued locally unless full backend/keeper settlement pipeline is active.

## 5) Quick Go/No-Go Rules Before Recording

Go if all are true:
1. Debate page updates at least twice in Demo Mode within 25 seconds.
2. Wallet connect button can reach connected address state.
3. Stake submission shows feedback message.
4. Agents and History pages respond to input and navigation.

No-Go if any are true:
1. Debate page remains static for 25+ seconds in Demo Mode.
2. Red error panel persists for 30+ seconds in Normal Mode.
3. Wallet button never opens a wallet prompt.

## 6) Fast Recovery Playbook (If Demo Breaks Mid-Recording)

1. Open Settings and switch Demo Mode ON.
2. Keep Auto-refresh ON.
3. Hard refresh browser tab.
4. Return to /debate/demo-session and wait 10 to 15 seconds.
5. Resume recording from debate movement proof.

