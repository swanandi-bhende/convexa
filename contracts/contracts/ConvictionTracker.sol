// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

contract ConvictionTracker {
    struct RoundResult {
        uint256 roundNumber;
        uint256 bullScore;
        uint256 bearScore;
        address winner;
        uint256 timestamp;
    }

    address immutable public owner;
    address public judgeAgent;
    uint256 public currentBullScore = 50;
    uint256 public currentBearScore = 50;
    uint256 public currentRound;
    uint256 immutable public winThreshold;
    uint256 constant public maxRounds = 20;
    bool public debateActive;
    bool public settlementTriggered;
    RoundResult[] public roundHistory;

    event ConvictionUpdated(
        uint256 indexed roundNumber,
        uint256 bullScore,
        uint256 bearScore,
        uint256 timestamp
    );
    event DebateWinnerDeclared(
        string winningSide,
        uint256 finalBullScore,
        uint256 finalBearScore,
        uint256 winningRound
    );
    event DebateSessionStarted(uint256 winThreshold, uint256 timestamp);
    event JudgeAgentUpdated(address indexed oldJudge, address indexed newJudge);

    constructor(address _judgeAgent, uint256 _winThreshold) {
        require(_judgeAgent != address(0), "Invalid judge address");
        owner = msg.sender;
        judgeAgent = _judgeAgent;
        winThreshold = _winThreshold == 0 ? 70 : _winThreshold;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    modifier onlyJudge() {
        require(msg.sender == judgeAgent, "Only judge agent can update conviction");
        _;
    }

    function updateConviction(
        uint256 bullScore,
        uint256 bearScore,
        uint256 roundNumber
    ) external onlyJudge {
        require(bullScore <= 100, "Bull score must be between 0 and 100");
        require(bearScore <= 100, "Bear score must be between 0 and 100");
        require(debateActive, "Debate is not active");
        require(!settlementTriggered, "Settlement already triggered");
        require(roundNumber == currentRound + 1, "Invalid round number");

        currentBullScore = bullScore;
        currentBearScore = bearScore;
        currentRound = roundNumber;

        roundHistory.push(
            RoundResult({
                roundNumber: roundNumber,
                bullScore: bullScore,
                bearScore: bearScore,
                winner: address(0),
                timestamp: block.timestamp
            })
        );

        emit ConvictionUpdated(roundNumber, bullScore, bearScore, block.timestamp);

        if (bullScore >= winThreshold) {
            debateActive = false;
            settlementTriggered = true;
            roundHistory[roundHistory.length - 1].winner = address(1);
            emit DebateWinnerDeclared("BULL", bullScore, bearScore, roundNumber);
        } else if (bearScore >= winThreshold) {
            debateActive = false;
            settlementTriggered = true;
            roundHistory[roundHistory.length - 1].winner = address(2);
            emit DebateWinnerDeclared("BEAR", bullScore, bearScore, roundNumber);
        } else if (currentRound >= maxRounds) {
            debateActive = false;
        }
    }

    function getCurrentScores()
        external
        view
        returns (uint256 bullScore, uint256 bearScore, uint256 roundNumber, bool isActive)
    {
        return (currentBullScore, currentBearScore, currentRound, debateActive);
    }

    function getRoundHistory() external view returns (RoundResult[] memory) {
        return roundHistory;
    }

    function getRound(uint256 roundNumber) external view returns (RoundResult memory) {
        require(roundNumber > 0 && roundNumber <= roundHistory.length, "Round out of range");
        return roundHistory[roundNumber - 1];
    }

    function isSettlementTriggered() external view returns (bool) {
        return settlementTriggered;
    }

    function startDebate() external onlyOwner {
        require(!debateActive, "Debate already active");
        require(!settlementTriggered, "Settlement already triggered");

        currentBullScore = 50;
        currentBearScore = 50;
        currentRound = 0;
        debateActive = true;
        settlementTriggered = false;
        delete roundHistory;

        emit DebateSessionStarted(winThreshold, block.timestamp);
    }

    function updateJudgeAgent(address newJudgeAgent) external onlyOwner {
        require(newJudgeAgent != address(0), "Invalid judge address");
        address oldJudge = judgeAgent;
        judgeAgent = newJudgeAgent;
        emit JudgeAgentUpdated(oldJudge, newJudgeAgent);
    }
}