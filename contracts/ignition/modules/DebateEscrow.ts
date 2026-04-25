import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

const DebateEscrowModule = buildModule("DebateEscrowModule", (m) => {
  const executorAddress = m.getParameter(
    "executorAddress",
    process.env.KEEPERHUB_EXECUTOR_ADDRESS || "0x000000000000000000000000000000000000dEaD"
  );

  const debateEscrow = m.contract("DebateEscrow", [executorAddress]);

  return { debateEscrow };
});

export default DebateEscrowModule;
