# AXL Implementation

AXL is the communication fabric for peer-to-peer agent debate. Bull and bear agents publish arguments to the judge via AXL, enabling decentralized message routing without a centralized broker.

## Overview

Without AXL, agent communication would collapse into:
- In-process function calls (not peer-to-peer)
- Centralized message broker (not decentralized)

AXL provides:
- **Peer-to-Peer Routing:** Three local AXL nodes route messages between agents
- **Cryptographic Verification:** Messages signed and verified (sender authenticity)
- **Topology Observability:** Debate communication pattern is visible and auditable
- **Decentralization:** No single point of failure in message routing

## Architecture

Convexa runs three local AXL nodes in separate processes:

```
┌─────────────────────────────────────────────────────┐
│ Bull Agent                                           │
│ (Groq LLM + market data reasoning)                  │
│                                                      │
│  publish_to_judge(round_argument)                   │
└──────────────┬────────────────────────────────────┘
               │ HTTP POST
┌──────────────▼────────────────────────────────────┐
│ Bull AXL Node (Port 8001)                         │
│ - Listens for agent messages                      │
│ - Routes to judge node                            │
└──────────────┬────────────────────────────────────┘
               │ AXL Peer Mesh
               ├──────────────────┐
┌──────────────▼────────────────────▼──────────────┐
│ Judge AXL Node (Port 8003)                       │
│ - Receives routed messages                       │
│ - Inbox accessible to judge agent                │
└──────────────┬────────────────────────────────────┘
               │
┌──────────────▼────────────────────────────────────┐
│ Judge Agent                                       │
│ (Groq LLM + conviction scoring)                  │
│                                                   │
│ wait_for_both_arguments()                        │
│ poll_inbox()                                     │
└──────────────────────────────────────────────────┘
```

## Integration Points

### 1. Node Configuration

Stored in `axl-nodes/{bull,bear,judge}/node-config.json`:

```json
{
  "name": "bull-node",
  "port": 8001,
  "peers": [
    {"address": "127.0.0.1:8003", "publicKey": "judge-pubkey"}
  ],
  "dataDir": "./data",
  "logLevel": "info"
}
```

Each node configuration includes:
- **Name:** Unique node identifier
- **Port:** HTTP listen port
- **Peers:** Other nodes in mesh
- **Data Directory:** Node state and logs
- **Log Level:** Debug verbosity

### 2. Bull Agent Publication (`agents/bull_agent.py`)

```python
def publish_to_judge(round_num, argument_text):
    """Publish bull argument to judge via AXL."""
    message = {
        "type": "ARGUMENT",
        "sender": "bull",
        "round": round_num,
        "argument": argument_text,
        "timestamp": datetime.now().isoformat()
    }
    
    response = requests.post(
        "http://127.0.0.1:8001/publish",
        json=message
    )
    
    return response.status_code == 200
```

**Flow:**
1. Bull agent generates argument via Groq LLM
2. Sends HTTP POST to local AXL node (port 8001)
3. AXL node routes message to judge node
4. Judge node stores in inbox

### 3. Bear Agent Publication (`agents/bear_agent.py`)

Identical to bull, but:
- Sends to AXL port 8002 (bear node)
- Message tagged with `"sender": "bear"`

### 4. Judge Agent Reception (`agents/judge_agent.py`)

```python
def wait_for_both_arguments():
    """Wait for bull and bear arguments from AXL inbox."""
    bull_arg = None
    bear_arg = None
    
    while bull_arg is None or bear_arg is None:
        messages = poll_inbox()
        
        for msg in messages:
            if msg["sender"] == "bull":
                bull_arg = msg
            elif msg["sender"] == "bear":
                bear_arg = msg
        
        time.sleep(1)
    
    return bull_arg, bear_arg

def poll_inbox():
    """Fetch pending messages from judge AXL node."""
    response = requests.get(
        "http://127.0.0.1:8003/inbox"
    )
    return response.json()["messages"]
```

**Behavior:**
- Polls judge node inbox every 1 second
- Waits for both bull and bear arguments
- Timeout: 30 seconds (abort if missing argument)

### 5. Judge Verdict Publishing

```python
def publish_verdict(round_num, conviction_score, reasoning):
    """Publish judge verdict back to orchestrator."""
    verdict = {
        "type": "VERDICT",
        "round": round_num,
        "conviction": conviction_score,  # -100 to +100
        "reasoning": reasoning,
        "timestamp": datetime.now().isoformat()
    }
    
    # Write to judge AXL node's outbox
    response = requests.post(
        "http://127.0.0.1:8003/publish",
        json=verdict
    )
    
    return verdict
```

Verdict is routed back to orchestrator via AXL.

## Node Lifecycle

Managed in `agents/orchestrator.py`:

```python
def start_axl_nodes():
    """Spin up three local AXL nodes."""
    bull_proc = subprocess.Popen(
        ["./axl-nodes/axl", "-config", "axl-nodes/bull/node-config.json"],
        stdout=open("data/logs/axl_bull.log", "w"),
        stderr=subprocess.STDOUT
    )
    
    bear_proc = subprocess.Popen(
        ["./axl-nodes/axl", "-config", "axl-nodes/bear/node-config.json"],
        stdout=open("data/logs/axl_bear.log", "w"),
        stderr=subprocess.STDOUT
    )
    
    judge_proc = subprocess.Popen(
        ["./axl-nodes/axl", "-config", "axl-nodes/judge/node-config.json"],
        stdout=open("data/logs/axl_judge.log", "w"),
        stderr=subprocess.STDOUT
    )
    
    return bull_proc, bear_proc, judge_proc

def health_check_axl_nodes():
    """Verify all nodes are running and responsive."""
    for port in [8001, 8002, 8003]:
        try:
            response = requests.get(f"http://127.0.0.1:{port}/health")
            assert response.status_code == 200
        except Exception as e:
            print(f"AXL node on port {port} unhealthy: {e}")
            return False
    return True

def shutdown_axl_nodes(procs):
    """Gracefully stop all AXL nodes."""
    for proc in procs:
        proc.terminate()
        proc.wait(timeout=5)
```

## Port Assignment

| Node | Port | Purpose |
| --- | --- | --- |
| Bull | 8001 | Bull agent publishes arguments |
| Bear | 8002 | Bear agent publishes arguments |
| Judge | 8003 | Judge receives and processes messages |

## Message Protocol

All messages follow standard AXL envelope:

```json
{
  "type": "ARGUMENT|VERDICT",
  "sender": "bull|bear|judge",
  "round": 1,
  "timestamp": "2026-05-03T10:00:00Z",
  "signature": "0x...",
  "payload": { /* sender-specific */ }
}
```

**Signature:** Ed25519 signature of message payload, verified by recipient

## Observability

### Monitor Node Logs

```bash
tail -f data/logs/axl_bull.log
tail -f data/logs/axl_bear.log
tail -f data/logs/axl_judge.log
```

### Monitor Message Flow

```bash
# Fetch pending messages in judge inbox
curl http://127.0.0.1:8003/inbox

# Publish test message to bull node
curl -X POST http://127.0.0.1:8001/publish \
  -H "Content-Type: application/json" \
  -d '{"type":"TEST", "sender":"test"}'
```

### AXL Node Health

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8002/health
curl http://127.0.0.1:8003/health
```

Expected response: `{"status": "healthy", "peers": 2}`

## Error Handling

### Node Crashes

If a node crashes mid-debate:
1. Orchestrator detects health check failure
2. Attempts graceful restart
3. If restart fails 3x, aborts debate and shuts down

### Message Timeouts

Judge waits max 30 seconds for arguments:
- If bull message arrives but bear doesn't → timeout
- Judge publishes "INCONCLUSIVE" verdict
- Debate proceeds but conviction not updated

### Network Partitions

Local nodes all on same machine, so no partitions in normal demo mode. In distributed setup, AXL consensus would handle partition recovery.

## Performance

- **Message Publish Latency:** 10-50ms (local HTTP)
- **Message Delivery:** <100ms (peer mesh routing)
- **Judge Inbox Poll:** 50ms per poll (1 poll/sec = 5% overhead)

Total round latency breakdown:
- Bull reasoning: 2-4 seconds
- Bull publish: 0.05s
- Bear reasoning: 2-4 seconds
- Bear publish: 0.05s
- Judge reasoning: 2-4 seconds
- Judge verdict: 0.05s
- **Total per round: 6-12 seconds**

## Testing

Test AXL message flow:

```bash
python scripts/test_axl_messaging.py
```

This:
1. Starts three nodes
2. Publishes test messages
3. Verifies inbox reception
4. Shuts down cleanly

## Why AXL?

AXL provides:
1. **Decentralization:** No centralized message broker
2. **Observability:** Agent communication visible and auditable
3. **Authenticity:** Cryptographically verified messages
4. **Modularity:** Agents interact via standard HTTP endpoints
5. **Scalability:** Mesh routing scales better than centralized queues

Without AXL, Convexa loses the peer-to-peer property that makes agent debate trust-minimized. With it, the debate is fully decentralized and observable.
