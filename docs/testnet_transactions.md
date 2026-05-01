# Testnet Transactions

Network: Unichain Sepolia (chain id 1301)
Explorer: https://sepolia.uniscan.xyz/

## V1 16 Completion Summary

**Completed**
- Deployed DebateEscrow and ConvictionTracker on Unichain Sepolia.
- Patched the orchestrator so recovery uses the agent wallet as the settlement executor.
- Ran a live debate session end-to-end with real onchain conviction update and final settlement.
- Captured the live deployment, conviction, and settlement hashes in this log.
- Fixed the recovery path so redeploy no longer blocks on the wrong executor or interactive Hardhat prompts.

**Failed or Not Fully Completed**
- The escrow was not seeded to 0.1 ETH per side; live runs used 0.001 ETH per side instead.
- The requested full 10-round live debate did not complete to round 10 because BEAR crossed the threshold in round 1 and the session ended early by design.
- A second independent full run was not completed.
- Explorer screenshots for every transaction were not collected.
- KeeperHub dashboard verification, slippage analysis, and full Uniswap proof chain documentation were not completed.

**Primary Failure Causes**
- Settlement executor mismatch: the first escrow deployment used KeeperHub executor ownership, but the available signing key was the agent wallet.
- Hardhat Ignition recovery initially failed because the orchestrator used unsupported flags and relied on brittle console parsing.
- The debate logic itself ended the session early when conviction threshold was reached, so 10 rounds never executed.
- Some requested submission artifacts require browser-based verification and screenshots that were not gathered in this workspace session.

## Current Verified Session

- Escrow deployment tx: 8fec67c3ee80edff309fb4019386d92fdbccfcf26f1275a7c6f548f6747d90ed
- Bull deposit tx: 8fb8ac8d54a1283d37c6e46a5579b3604fdaf2d7112a6a7bd352eef236ca40bc
- Bear deposit tx: 6f449919216a0db6a139b0eabcd46efdbba36556f64eead4d2ce27ba11481fdf

## 16.5 Smoke Test In Progress

- round 1 session id: 5cea3576-e8e7-47cb-a0a1-09a8f4dac465
- startDebate tx: 8fec67c3ee80edff309fb4019386d92fdbccfcf26f1275a7c6f548f6747d90ed
- bull deposit tx: 8fb8ac8d54a1283d37c6e46a5579b3604fdaf2d7112a6a7bd352eef236ca40bc
- bear deposit tx: 6f449919216a0db6a139b0eabcd46efdbba36556f64eead4d2ce27ba11481fdf
- conviction update tx: b1ffdef702afdbcdb9ae0e3fc6c8746b7d860a30d0f124360735028c3f6025a6
- final settlement tx: 98bf50476ba68d4d3a5e3f82177b0198e75c8d75ef9edbdc0edb1a18a9f162ee
- smoke result: completed, winner bear

## 16.4 Escrow Seeding

- startDebate tx: fbaaa3d6bfe084ffc146da3c62f60c5429bd8d51affe9257a2d8c4c1a3c6148b
- bull deposit (0.09 ETH) tx: abfa825df3a09308ecf3970ce5004cc777bde4fafea7984fff66223bc7217f74
- bear deposit (0.09 ETH) tx: de33f60ded776b9094c9d5c70232146af7301586aa575ed333716ccaec1c7e0d

## 16.5 Smoke Test (1 round)

- updateConviction tx: b1ffdef702afdbcdb9ae0e3fc6c8746b7d860a30d0f124360735028c3f6025a6
- final settlement tx: 98bf50476ba68d4d3a5e3f82177b0198e75c8d75ef9edbdc0edb1a18a9f162ee

## 16.6 Full 10-Round Debate (1st Attempt - Conviction Early Settlement)

**Status:** Partially completed - Early termination when bear reached win threshold (73 points)

- session_id: 4d6bb760-b2df-43c0-8f8e-c3681f5bc774
- escrow_start_tx: 14a2339dc866aba6937434fd8acc8c9111283783f76ca0eba8d2ca2110eaa7f6
- conviction_start_tx: 648202e25707569bde18b7689f977c78c4b31fd959fce9d4b2b7dc61d71dafae
- bull_deposit_tx: f15d58238df8d3bda51a7c8fe63a56746e495d572cedce27a739826c6b45927a
- bear_deposit_tx: a7f29c93b03d47715621af174cd4e0952c61d6ef487d895465d565f72df42647

**Round 1 Results:**
- Round duration: 97.43s
- Winner: BEAR (73-5)
- conviction_update_tx: 7754f8f00455f8a5cb84411f049010c9d60442a3dc3e65c5c03ea78e87f55f9b ✅
- final_settlement_tx: 405bc3303f86117a5e787375b495d54866813f6b16825f769acff7e3d9268731 ❌ (reverted)

**Issues Encountered:**
1. **AXL Peer ID Mismatch:** Both bull and bear agents flagged peer_id_mismatch warnings (separate issue requiring AXL identity validation)
2. **Conviction Settlement Conflict:** ConvictionTracker already marked as settled after round 1, blocking final escrow settlement
3. **Early Termination:** Debate ended after round 1 when bear reached 73 points (threshold: 70)

**Evidence Collected:**
- ✅ Escrow initialization working
- ✅ Stake deposits successful
- ✅ Round execution and judgment working
- ✅ Conviction update transaction successful (on-chain verdict recorded)
- ❌ Final settlement failed (contract state conflict)

## 16.7 Full 10-Round Debate (2nd Attempt - Clean Settlement)

**Status:** Completed successfully - redeployed fresh ConvictionTracker and settled on-chain with the agent wallet executor

- session_id: fdf5ae83-4522-4f74-ada7-3a84fd291e85
- escrow_start_tx: 5843b268f04581e3afc544f7aa63e077a29bdd305d2f3fc396d24c416beb7a31
- conviction_start_tx: a5fcc6ee3ab4277c9cd1b61225b05881c2fb654c503a34ddd540f91a3482cdba
- bull_deposit_tx: 81bbbf738fb43f6b985944ec2f9807eda644c6f35b0c54cb2a4f7c71a1dc11f7
- bear_deposit_tx: 386b426e1dff44574a6fe58cf9a827c5909199641410be9514f9a93cac77ccac

**Round 1 Results:**
- Round duration: 98.32s
- Winner: BEAR (73-5)
- conviction_update_tx: c0b1a31b3601c660550dd222230ff39f61e89b9cd88e362ebf69494f7604e1bb ✅

**Final Settlement:**
- settlement_tx: ed40d33873d8c8326e31fb2af326b663f929f08d3f865b9446866516d3b0d498 ✅
- final result: completed successfully
- note: debate ended after round 1 because bear reached the 70-point win threshold

**Evidence Collected:**
- ✅ Fresh DebateEscrow and ConvictionTracker redeployed cleanly
- ✅ Stake deposits successful
- ✅ Round 1 judgment and conviction update successful
- ✅ Final settlement executed successfully from the agent wallet
