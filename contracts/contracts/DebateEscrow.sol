// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

contract DebateEscrow {
    enum Side {
        BULL,
        BEAR
    }

    address immutable public owner;
    address immutable public settlementExecutor;

    bool public debateActive;
    uint256 public debateStartTime;
    uint256 public debateEndTime;

    mapping(address => mapping(Side => uint256)) public userStakes;
    mapping(Side => uint256) public totalStaked;
    address[] public stakers;

    event Deposited(address indexed user, Side side, uint256 amount);
    event Settled(Side winningSide, uint256 totalPayout);
    event DebateStarted(uint256 startTime, uint256 endTime);
    event DebatePaused(string reason);

    constructor(address _settlementExecutor) {
        require(_settlementExecutor != address(0), "Invalid executor address");
        owner = msg.sender;
        settlementExecutor = _settlementExecutor;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    modifier onlyExecutor() {
        require(msg.sender == settlementExecutor, "Only settlement executor");
        _;
    }

    modifier debateIsActive() {
        require(debateActive, "Debate is not active");
        require(block.timestamp <= debateEndTime, "Debate window closed");
        _;
    }

    function startDebate(uint256 durationSeconds) external onlyOwner {
        require(!debateActive, "Debate already active");

        debateActive = true;
        debateStartTime = block.timestamp;
        debateEndTime = block.timestamp + durationSeconds;

        totalStaked[Side.BULL] = 0;
        totalStaked[Side.BEAR] = 0;
        delete stakers;

        emit DebateStarted(debateStartTime, debateEndTime);
    }

    function deposit(Side side) external payable debateIsActive {
        require(msg.value >= 0.001 ether, "Minimum stake is 0.001 ETH");

        if (
            userStakes[msg.sender][Side.BULL] == 0 &&
            userStakes[msg.sender][Side.BEAR] == 0
        ) {
            stakers.push(msg.sender);
        }

        userStakes[msg.sender][side] += msg.value;
        totalStaked[side] += msg.value;

        emit Deposited(msg.sender, side, msg.value);
    }

    function settleSide(Side winner) external onlyExecutor {
        // CHECKS: Validate preconditions
        require(debateActive, "Debate is not active");
        
        Side loser = winner == Side.BULL ? Side.BEAR : Side.BULL;
        uint256 winnerPool = totalStaked[winner];
        uint256 loserPool = totalStaked[loser];
        require(winnerPool > 0, "No stakes on winning side");
        
        // EFFECTS: Update all state variables BEFORE external calls
        // First, save all winner stakes before clearing (necessary for later payout calculation)
        address[] memory stakersSnapshot = stakers;
        uint256[] memory winnerStakes = new uint256[](stakersSnapshot.length);
        
        for (uint256 i = 0; i < stakersSnapshot.length; i++) {
            winnerStakes[i] = userStakes[stakersSnapshot[i]][winner];
        }
        
        debateActive = false;
        uint256 totalPayout = winnerPool + loserPool;
        
        // Clear all user stakes and pool totals
        for (uint256 i = 0; i < stakersSnapshot.length; i++) {
            address staker = stakersSnapshot[i];
            userStakes[staker][Side.BULL] = 0;
            userStakes[staker][Side.BEAR] = 0;
        }
        
        totalStaked[Side.BULL] = 0;
        totalStaked[Side.BEAR] = 0;
        delete stakers;
        
        // Emit event before external calls
        emit Settled(winner, totalPayout);
        
        // INTERACT: Make external calls LAST
        for (uint256 i = 0; i < stakersSnapshot.length; i++) {
            if (winnerStakes[i] > 0) {
                uint256 share = (winnerStakes[i] * loserPool) / winnerPool;
                uint256 payout = winnerStakes[i] + share;
                (bool sent, ) = payable(stakersSnapshot[i]).call{value: payout}("");
                require(sent, "Payout transfer failed");
            }
        }
    }

    function getStakeInfo()
        external
        view
        returns (uint256 bullTotal, uint256 bearTotal, bool isDebateActive)
    {
        return (totalStaked[Side.BULL], totalStaked[Side.BEAR], debateActive);
    }

    function getUserStake(address user)
        external
        view
        returns (uint256 bullStake, uint256 bearStake)
    {
        return (userStakes[user][Side.BULL], userStakes[user][Side.BEAR]);
    }

    function getStakers() external view returns (address[] memory) {
        return stakers;
    }

    function emergencyPause(string calldata reason) external onlyOwner {
        debateActive = false;
        emit DebatePaused(reason);
    }
}
