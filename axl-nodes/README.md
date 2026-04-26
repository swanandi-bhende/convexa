# axl-nodes

This directory contains the three isolated AXL nodes used by the debate agents.
Each node has its own config, identity key, listening port, and message queue so
the Bull, Bear, and Judge agents communicate over separate local AXL peers
rather than a centralized broker.

## Topology

- Bull node API: `http://127.0.0.1:8001`
- Bear node API: `http://127.0.0.1:8002`
- Judge node API: `http://127.0.0.1:8003`

Each node uses its own `data/private.pem` identity file. If you delete a node's
data directory, AXL will generate a fresh identity on the next startup.

The bundled binary currently exposes `-config` and `-listen` flags. The shipped
build does not print a version string, so the practical installation check is to
start a node and confirm it reports its public key and listening ports.

## Peer IDs On This Machine

These were generated on the current machine during the last successful startup.
They will be different on a fresh clone or after deleting a node's data folder.

- Bull: `520cda07fce54eb2f43a1a016aea85553e2ef7d0e32bcce91e2a58bd79f876ae`
- Bear: `5e6b45ce2a4eeb5bf861815f91152c7f8d56178a335fa3db046048b882d48de0`
- Judge: `858fa91d81feaa82624609a37b1a6a2b945d2c26e8bc57db7f37f26f59687e5b`

## Start Manually

From the repo root:

```bash
cd axl-nodes/bull && ../axl -config node-config.json
cd axl-nodes/bear && ../axl -config node-config.json
cd axl-nodes/judge && ../axl -config node-config.json
```

## Start All Nodes

```bash
./axl-nodes/start-all.sh
```

## Stop All Nodes

```bash
./axl-nodes/stop-all.sh
```

## Mesh Smoke Test

```bash
./axl-nodes/test-mesh.sh
```

## Troubleshooting

If peer discovery fails, check that each config lists the other nodes in `Peers`
and that the `data/private.pem` files still exist. If the peer IDs changed,
delete the data directory and restart all nodes to regenerate identities.

If ports 8001, 8002, or 8003 are already in use, stop the conflicting process
or change the node API ports before restarting.

If macOS blocks the binary, open System Settings, allow the app from Security,
and retry. The binary is ignored by git and should remain local only.
