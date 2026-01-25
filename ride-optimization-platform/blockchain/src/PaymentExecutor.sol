// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title PaymentExecutor
 * @notice Records off-chain ETH payment execution for audit trail
 * @dev This contract does NOT hold or transfer ETH.
 *      It serves as an on-chain audit log for payments executed via x402 protocol.
 *      
 *      Payment flow:
 *      1. Agentic AI monitors AuctionFinalized event from RideAuction
 *      2. AI converts quotedCostScaled to ETH using Chainlink oracle (off-chain)
 *      3. AI executes ETH payment via x402 protocol
 *      4. AI calls recordPayment() to log the transaction on-chain
 */
contract PaymentExecutor {
    // =========================================================================
    // STRUCTS
    // =========================================================================

    struct PaymentRecord {
        bytes32 bundleHash;         // The bundle this payment is for
        address winner;             // The winning company
        uint256 amountPaidScaled;   // Amount paid in ETH (scaled by 1e18)
        bytes32 txHash;             // Off-chain transaction hash for reference
        uint256 timestamp;          // When payment was recorded
        bool recorded;              // Whether payment has been recorded
    }

    // =========================================================================
    // STATE VARIABLES
    // =========================================================================

    /// @notice Owner of the contract
    address public owner;

    /// @notice Reference to the RideAuction contract
    address public rideAuction;

    /// @notice Authorized payment recorders (Agentic AI addresses)
    mapping(address => bool) public authorizedRecorders;

    /// @notice Payment records indexed by bundleHash
    mapping(bytes32 => PaymentRecord) public payments;

    // =========================================================================
    // EVENTS
    // =========================================================================

    event PaymentExecuted(
        bytes32 indexed bundleHash,
        address indexed winner,
        uint256 amountPaidScaled,
        bytes32 txHash
    );

    event RecorderAuthorized(address indexed recorder);
    event RecorderRevoked(address indexed recorder);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event RideAuctionSet(address indexed rideAuction);

    // =========================================================================
    // ERRORS
    // =========================================================================

    error OnlyOwner();
    error OnlyAuthorizedRecorder();
    error PaymentAlreadyRecorded();
    error InvalidWinner();
    error InvalidAmount();

    // =========================================================================
    // MODIFIERS
    // =========================================================================

    modifier onlyOwner() {
        if (msg.sender != owner) revert OnlyOwner();
        _;
    }

    modifier onlyAuthorizedRecorder() {
        if (!authorizedRecorders[msg.sender]) revert OnlyAuthorizedRecorder();
        _;
    }

    // =========================================================================
    // CONSTRUCTOR
    // =========================================================================

    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    // =========================================================================
    // ADMIN FUNCTIONS
    // =========================================================================

    /**
     * @notice Transfer ownership to a new address
     * @param newOwner The address of the new owner
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "New owner is zero address");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    /**
     * @notice Set the RideAuction contract address
     * @param _rideAuction Address of the RideAuction contract
     */
    function setRideAuction(address _rideAuction) external onlyOwner {
        require(_rideAuction != address(0), "Invalid auction address");
        rideAuction = _rideAuction;
        emit RideAuctionSet(_rideAuction);
    }

    /**
     * @notice Authorize an address to record payments
     * @param recorder Address to authorize (typically Agentic AI)
     */
    function authorizeRecorder(address recorder) external onlyOwner {
        require(recorder != address(0), "Invalid recorder address");
        authorizedRecorders[recorder] = true;
        emit RecorderAuthorized(recorder);
    }

    /**
     * @notice Revoke authorization from a recorder
     * @param recorder Address to revoke
     */
    function revokeRecorder(address recorder) external onlyOwner {
        authorizedRecorders[recorder] = false;
        emit RecorderRevoked(recorder);
    }

    // =========================================================================
    // PAYMENT RECORDING
    // =========================================================================

    /**
     * @notice Record an off-chain payment execution
     * @dev Called by Agentic AI after executing ETH payment via x402
     * @param bundleHash The bundle this payment is for
     * @param winner The winning company address
     * @param amountPaidScaled Amount paid in ETH (scaled by 1e18)
     * @param txHash The off-chain transaction hash for reference
     */
    function recordPayment(
        bytes32 bundleHash,
        address winner,
        uint256 amountPaidScaled,
        bytes32 txHash
    ) external onlyAuthorizedRecorder {
        // Validate inputs
        if (winner == address(0)) revert InvalidWinner();
        if (amountPaidScaled == 0) revert InvalidAmount();
        if (payments[bundleHash].recorded) revert PaymentAlreadyRecorded();

        // Record payment
        payments[bundleHash] = PaymentRecord({
            bundleHash: bundleHash,
            winner: winner,
            amountPaidScaled: amountPaidScaled,
            txHash: txHash,
            timestamp: block.timestamp,
            recorded: true
        });

        emit PaymentExecuted(bundleHash, winner, amountPaidScaled, txHash);
    }

    // =========================================================================
    // VIEW FUNCTIONS
    // =========================================================================

    /**
     * @notice Get payment record for a bundle
     * @param bundleHash The bundle to query
     * @return winner The winning company
     * @return amountPaidScaled Amount paid (1e18 scaled)
     * @return txHash Off-chain transaction hash
     * @return timestamp When payment was recorded
     * @return recorded Whether payment was recorded
     */
    function getPayment(bytes32 bundleHash) external view returns (
        address winner,
        uint256 amountPaidScaled,
        bytes32 txHash,
        uint256 timestamp,
        bool recorded
    ) {
        PaymentRecord storage payment = payments[bundleHash];
        return (
            payment.winner,
            payment.amountPaidScaled,
            payment.txHash,
            payment.timestamp,
            payment.recorded
        );
    }

    /**
     * @notice Check if an address is an authorized recorder
     * @param recorder Address to check
     * @return isAuthorized Whether the address can record payments
     */
    function isAuthorizedRecorder(address recorder) external view returns (bool isAuthorized) {
        return authorizedRecorders[recorder];
    }

    /**
     * @notice Check if a payment has been recorded for a bundle
     * @param bundleHash The bundle to check
     * @return isRecorded Whether payment is recorded
     */
    function isPaymentRecorded(bytes32 bundleHash) external view returns (bool isRecorded) {
        return payments[bundleHash].recorded;
    }
}
