import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

const ConvictionTrackerModule = buildModule("ConvictionTrackerModule", (m) => {
  const configuredAgentAddress = process.env.AGENT_WALLET_ADDRESS;
  const judgeAgentAddress =
    configuredAgentAddress && !configuredAgentAddress.includes("your_agent_wallet_address")
      ? configuredAgentAddress
      : process.env.KEEPERHUB_EXECUTOR_ADDRESS || "0x000000000000000000000000000000000000dEaD";

  const convictionTracker = m.contract("ConvictionTracker", [judgeAgentAddress, 70]);

  return { convictionTracker };
});

export default ConvictionTrackerModule;