// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title RideAuction
 * @notice Sealed-bid commit-reveal auction for AI-optimized ride bundles
 * @dev Trust-minimized auction where:
 *      - Backend creates auctions with bundleHash
 *      - Whitelisted companies commit bids (hidden)
 *      - Companies reveal bids within time window
 *      - Contract deterministically selects lowest bidder
 *      - No ETH custody, no oracle calls, no sensitive data on-chain
 */
contract RideAuction {
    // =========================================================================
    // STRUCTS
    // =========================================================================

    struct Auction {
        uint256 commitStartTime;    // When commit phase starts
        uint256 commitEndTime;      // When commit phase ends (reveal starts)
        uint256 revealEndTime;      // When reveal phase ends
        bool finalized;             // Whether auction has been finalized
        address winner;             // Winning bidder address
        uint256 winningBid;         // Winning bid amount (scaled by 1e18)
        uint256 revealCounter;      // Counter for reveal order
        uint256 bidCount;           // Number of committed bids
    }

    struct BidCommitment {
        bytes32 hash;               // keccak256(bundleHash, bidder, quotedCostScaled, salt)
        bool revealed;              // Whether bid has been revealed
        uint256 quotedCostScaled;   // Revealed bid amount (1e18 scaled)
        uint256 revealOrder;        // Order in which bid was revealed (for tie-breaking)
    }

    // =========================================================================
    // STATE VARIABLES
    // =========================================================================

    /// @notice Owner of the contract (can manage bidders)
    address public owner;

    /// @notice Mapping from bundleHash to Auction
    mapping(bytes32 => Auction) public auctions;

    /// @notice Mapping from bundleHash to bidder address to their commitment
    mapping(bytes32 => mapping(address => BidCommitment)) public commitments;

    /// @notice Whitelisted bidder addresses
    mapping(address => bool) public bidders;

    /// @notice Array of bidder addresses per auction (for iteration)
    mapping(bytes32 => address[]) public auctionBidders;

    /// @notice Commit window duration in seconds
    uint256 public constant COMMIT_DURATION = 300; // 5 minutes

    /// @notice Reveal window duration in seconds
    uint256 public constant REVEAL_DURATION = 120; // 2 minutes

    /// @notice Maximum number of bidders per auction
    uint256 public constant MAX_BIDDERS = 20;

    // =========================================================================
    // EVENTS
    // =========================================================================

    event AuctionCreated(bytes32 indexed bundleHash, uint256 commitEndTime, uint256 revealEndTime);
    event BidCommitted(bytes32 indexed bundleHash, address indexed bidder);
    event BidRevealed(bytes32 indexed bundleHash, address indexed bidder, uint256 quotedCostScaled);
    event AuctionFinalized(bytes32 indexed bundleHash, address indexed winner, uint256 quotedCostScaled);
    event AuctionUnsold(bytes32 indexed bundleHash);
    event BidderAdded(address indexed bidder);
    event BidderRemoved(address indexed bidder);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    // =========================================================================
    // ERRORS
    // =========================================================================

    error OnlyOwner();
    error AuctionAlreadyExists();
    error AuctionDoesNotExist();
    error CommitPhaseNotActive();
    error RevealPhaseNotActive();
    error AuctionAlreadyFinalized();
    error AuctionNotReadyForFinalization();
    error BidderNotWhitelisted();
    error NoBidToReveal();
    error InvalidCommitmentHash();
    error BidAlreadyRevealed();
    error MaxBiddersReached();

    // =========================================================================
    // MODIFIERS
    // =========================================================================

    modifier onlyOwner() {
        if (msg.sender != owner) revert OnlyOwner();
        _;
    }

    modifier onlyWhitelistedBidder() {
        if (!bidders[msg.sender]) revert BidderNotWhitelisted();
        _;
    }

    modifier auctionExists(bytes32 bundleHash) {
        if (auctions[bundleHash].commitStartTime == 0) revert AuctionDoesNotExist();
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
     * @notice Add a whitelisted bidder
     * @param bidder Address to whitelist
     */
    function addBidder(address bidder) external onlyOwner {
        require(bidder != address(0), "Invalid bidder address");
        bidders[bidder] = true;
        emit BidderAdded(bidder);
    }

    /**
     * @notice Remove a whitelisted bidder
     * @param bidder Address to remove
     */
    function removeBidder(address bidder) external onlyOwner {
        bidders[bidder] = false;
        emit BidderRemoved(bidder);
    }

    // =========================================================================
    // AUCTION LIFECYCLE
    // =========================================================================

    /**
     * @notice Create a new auction for a ride bundle
     * @dev bundleHash must be unique and never reused
     * @param bundleHash keccak256 hash of the bundle_id (generated off-chain)
     */
    function createAuction(bytes32 bundleHash) external onlyOwner {
        // Ensure bundleHash has never been used
        if (auctions[bundleHash].commitStartTime != 0) revert AuctionAlreadyExists();

        uint256 commitStart = block.timestamp;
        uint256 commitEnd = commitStart + COMMIT_DURATION;
        uint256 revealEnd = commitEnd + REVEAL_DURATION;

        auctions[bundleHash] = Auction({
            commitStartTime: commitStart,
            commitEndTime: commitEnd,
            revealEndTime: revealEnd,
            finalized: false,
            winner: address(0),
            winningBid: 0,
            revealCounter: 0,
            bidCount: 0
        });

        emit AuctionCreated(bundleHash, commitEnd, revealEnd);
    }

    /**
     * @notice Commit a sealed bid for an auction
     * @dev bidHash = keccak256(abi.encodePacked(bundleHash, msg.sender, quotedCostScaled, salt))
     * @param bundleHash The auction's bundle hash
     * @param bidHash The commitment hash
     */
    function commitBid(bytes32 bundleHash, bytes32 bidHash) 
        external 
        onlyWhitelistedBidder 
        auctionExists(bundleHash) 
    {
        Auction storage auction = auctions[bundleHash];

        // Check commit phase is active
        if (block.timestamp < auction.commitStartTime || block.timestamp >= auction.commitEndTime) {
            revert CommitPhaseNotActive();
        }

        // Check max bidders
        if (auction.bidCount >= MAX_BIDDERS) revert MaxBiddersReached();

        // Store commitment (allows updating during commit phase)
        if (commitments[bundleHash][msg.sender].hash == bytes32(0)) {
            // First commitment from this bidder
            auctionBidders[bundleHash].push(msg.sender);
            auction.bidCount++;
        }

        commitments[bundleHash][msg.sender] = BidCommitment({
            hash: bidHash,
            revealed: false,
            quotedCostScaled: 0,
            revealOrder: 0
        });

        emit BidCommitted(bundleHash, msg.sender);
    }

    /**
     * @notice Reveal a previously committed bid
     * @param bundleHash The auction's bundle hash
     * @param quotedCostScaled The bid amount (scaled by 1e18)
     * @param salt The random salt used in commitment
     */
    function revealBid(bytes32 bundleHash, uint256 quotedCostScaled, bytes32 salt) 
        external 
        auctionExists(bundleHash) 
    {
        Auction storage auction = auctions[bundleHash];
        BidCommitment storage commitment = commitments[bundleHash][msg.sender];

        // Check reveal phase is active
        if (block.timestamp < auction.commitEndTime || block.timestamp >= auction.revealEndTime) {
            revert RevealPhaseNotActive();
        }

        // Check commitment exists
        if (commitment.hash == bytes32(0)) revert NoBidToReveal();

        // Check not already revealed
        if (commitment.revealed) revert BidAlreadyRevealed();

        // Verify commitment hash
        bytes32 computedHash = keccak256(abi.encodePacked(bundleHash, msg.sender, quotedCostScaled, salt));
        if (computedHash != commitment.hash) revert InvalidCommitmentHash();

        // Record reveal
        auction.revealCounter++;
        commitment.revealed = true;
        commitment.quotedCostScaled = quotedCostScaled;
        commitment.revealOrder = auction.revealCounter;

        emit BidRevealed(bundleHash, msg.sender, quotedCostScaled);
    }

    /**
     * @notice Finalize an auction and determine the winner
     * @dev Can be called after reveal window ends or when all bids are revealed
     * @param bundleHash The auction's bundle hash
     */
    function finalizeAuction(bytes32 bundleHash) external auctionExists(bundleHash) {
        Auction storage auction = auctions[bundleHash];

        // Check not already finalized
        if (auction.finalized) revert AuctionAlreadyFinalized();

        // Ensure commit phase is over
        if (block.timestamp < auction.commitEndTime) revert AuctionNotReadyForFinalization();

        // Check if ready for finalization
        bool allRevealed = _allBidsRevealed(bundleHash);
        bool revealEnded = block.timestamp >= auction.revealEndTime;

        if (!allRevealed && !revealEnded) revert AuctionNotReadyForFinalization();

        // Find winner (lowest bid, earliest reveal for tie-break)
        address winner = address(0);
        uint256 lowestBid = type(uint256).max;
        uint256 earliestReveal = type(uint256).max;

        address[] storage bidderList = auctionBidders[bundleHash];
        for (uint256 i = 0; i < bidderList.length && i < MAX_BIDDERS; i++) {
            BidCommitment storage bid = commitments[bundleHash][bidderList[i]];

            if (!bid.revealed) continue;

            // Check if this is the lowest bid OR tie-breaker
            if (bid.quotedCostScaled < lowestBid || 
                (bid.quotedCostScaled == lowestBid && bid.revealOrder < earliestReveal)) {
                lowestBid = bid.quotedCostScaled;
                earliestReveal = bid.revealOrder;
                winner = bidderList[i];
            }
        }

        // Mark as finalized
        auction.finalized = true;

        if (winner == address(0)) {
            // No valid bids - auction unsold
            emit AuctionUnsold(bundleHash);
        } else {
            auction.winner = winner;
            auction.winningBid = lowestBid;
            emit AuctionFinalized(bundleHash, winner, lowestBid);
        }
    }

    // =========================================================================
    // VIEW FUNCTIONS
    // =========================================================================

    /**
     * @notice Get auction details
     * @param bundleHash The auction's bundle hash
     * @return commitStartTime Start of commit phase
     * @return commitEndTime End of commit phase
     * @return revealEndTime End of reveal phase
     * @return finalized Whether auction is finalized
     * @return winner Winner address
     * @return winningBid Winning bid amount
     * @return bidCount Number of bids
     */
    function getAuction(bytes32 bundleHash) external view returns (
        uint256 commitStartTime,
        uint256 commitEndTime,
        uint256 revealEndTime,
        bool finalized,
        address winner,
        uint256 winningBid,
        uint256 bidCount
    ) {
        Auction storage auction = auctions[bundleHash];
        return (
            auction.commitStartTime,
            auction.commitEndTime,
            auction.revealEndTime,
            auction.finalized,
            auction.winner,
            auction.winningBid,
            auction.bidCount
        );
    }

    /**
     * @notice Get commitment details for a bidder
     * @param bundleHash The auction's bundle hash
     * @param bidder The bidder address
     * @return hash Commitment hash
     * @return revealed Whether revealed
     * @return quotedCostScaled Revealed bid amount
     * @return revealOrder Order of reveal
     */
    function getCommitment(bytes32 bundleHash, address bidder) external view returns (
        bytes32 hash,
        bool revealed,
        uint256 quotedCostScaled,
        uint256 revealOrder
    ) {
        BidCommitment storage commitment = commitments[bundleHash][bidder];
        return (
            commitment.hash,
            commitment.revealed,
            commitment.quotedCostScaled,
            commitment.revealOrder
        );
    }

    /**
     * @notice Get current auction phase
     * @param bundleHash The auction's bundle hash
     * @return phase 0=NotStarted, 1=Commit, 2=Reveal, 3=Finalized, 4=Expired
     */
    function getAuctionPhase(bytes32 bundleHash) external view returns (uint8 phase) {
        Auction storage auction = auctions[bundleHash];

        if (auction.commitStartTime == 0) return 0; // Not Started
        if (auction.finalized) return 3; // Finalized
        if (block.timestamp < auction.commitEndTime) return 1; // Commit Phase
        if (block.timestamp < auction.revealEndTime) return 2; // Reveal Phase
        return 4; // Expired (needs finalization)
    }

    /**
     * @notice Check if a bidder is whitelisted
     * @param bidder Address to check
     * @return isWhitelisted Whether bidder is whitelisted
     */
    function isBidderWhitelisted(address bidder) external view returns (bool isWhitelisted) {
        return bidders[bidder];
    }

    /**
     * @notice Compute commitment hash (helper for off-chain use)
     * @param bundleHash The auction's bundle hash
     * @param bidder The bidder address
     * @param quotedCostScaled The bid amount
     * @param salt The random salt
     * @return hash The commitment hash
     */
    function computeCommitmentHash(
        bytes32 bundleHash,
        address bidder,
        uint256 quotedCostScaled,
        bytes32 salt
    ) external pure returns (bytes32 hash) {
        return keccak256(abi.encodePacked(bundleHash, bidder, quotedCostScaled, salt));
    }

    // =========================================================================
    // INTERNAL FUNCTIONS
    // =========================================================================

    /**
     * @notice Check if all committed bids have been revealed
     * @param bundleHash The auction's bundle hash
     * @return allRevealed Whether all bids are revealed
     */
    function _allBidsRevealed(bytes32 bundleHash) internal view returns (bool allRevealed) {
        address[] storage bidderList = auctionBidders[bundleHash];
        for (uint256 i = 0; i < bidderList.length && i < MAX_BIDDERS; i++) {
            if (!commitments[bundleHash][bidderList[i]].revealed) {
                return false;
            }
        }
        return true;
    }
}
