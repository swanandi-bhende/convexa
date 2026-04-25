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

    address public owner;
    address public judgeAgent;
    uint256 public currentBullScore = 50;
    uint256 public currentBearScore = 50;
    uint256 public currentRound;
    uint256 public winThreshold;
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
    event JudgeAgentUpdated(address oldJudge, address newJudge);

    constructor(address _judgeAgent, uint256 _winThreshold) {
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

    function updateConviction(uint256 bullScore, uint256 bearScore) external onlyJudge {
        require(debateActive, "Debate is not active");
        require(!settlementTriggered, "Settlement already triggered");

        currentRound += 1;
        currentBullScore = bullScore;
        currentBearScore = bearScore;

        address winner = address(0);
        if (bullScore >= winThreshold && bullScore >= bearScore) {
            winner = address(1);
        } else if (bearScore >= winThreshold) {
            winner = address(2);
        }

        roundHistory.push(
            RoundResult({
                roundNumber: currentRound,
                bullScore: bullScore,
                bearScore: bearScore,
                winner: winner,
                timestamp: block.timestamp
            })
        );

        emit ConvictionUpdated(currentRound, bullScore, bearScore, block.timestamp);

        if (winner != address(0)) {
            debateActive = false;
            settlementTriggered = true;

            if (winner == address(1)) {
                emit DebateWinnerDeclared("BULL", bullScore, bearScore, currentRound);
            } else {
                emit DebateWinnerDeclared("BEAR", bullScore, bearScore, currentRound);
            }
        }
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
        address oldJudge = judgeAgent;
        judgeAgent = newJudgeAgent;
        emit JudgeAgentUpdated(oldJudge, newJudgeAgent);
    }
}