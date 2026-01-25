// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {RideAuction} from "../src/RideAuction.sol";

/**
 * @title RideAuctionTest
 * @notice Comprehensive tests for RideAuction contract
 */
contract RideAuctionTest is Test {
    RideAuction public auction;

    address public owner = address(this);
    address public bidder1 = makeAddr("bidder1");
    address public bidder2 = makeAddr("bidder2");
    address public bidder3 = makeAddr("bidder3");
    address public nonBidder = makeAddr("nonBidder");

    bytes32 public bundleHash = keccak256("bundle_001");

    function setUp() public {
        auction = new RideAuction();

        // Whitelist bidders
        console.log("Whitelisting bidder1:", bidder1);
        auction.addBidder(bidder1);
        auction.addBidder(bidder2);
        auction.addBidder(bidder3);
    }

    // =========================================================================
    // ADMIN TESTS
    // =========================================================================

    function test_OwnerIsDeployer() public view {
        assertEq(auction.owner(), owner);
    }

    function test_AddBidder() public {
        address newBidder = address(0x100);
        auction.addBidder(newBidder);
        assertTrue(auction.isBidderWhitelisted(newBidder));
    }

    function test_RemoveBidder() public {
        auction.removeBidder(bidder1);
        assertFalse(auction.isBidderWhitelisted(bidder1));
    }

    function test_OnlyOwnerCanAddBidder() public {
        vm.prank(bidder1);
        vm.expectRevert(RideAuction.OnlyOwner.selector);
        auction.addBidder(address(0x100));
    }

    function test_TransferOwnership() public {
        address newOwner = address(0x200);
        auction.transferOwnership(newOwner);
        assertEq(auction.owner(), newOwner);
    }

    // =========================================================================
    // AUCTION CREATION TESTS
    // =========================================================================

    function test_CreateAuction() public {
        auction.createAuction(bundleHash);

        (
            uint256 commitStartTime,
            uint256 commitEndTime,
            uint256 revealEndTime,
            bool finalized,
            address winner,
            uint256 winningBid,
            uint256 bidCount
        ) = auction.getAuction(bundleHash);

        assertEq(commitStartTime, block.timestamp);
        assertEq(commitEndTime, block.timestamp + 300);
        assertEq(revealEndTime, block.timestamp + 420);
        assertFalse(finalized);
        assertEq(winner, address(0));
        assertEq(winningBid, 0);
        assertEq(bidCount, 0);
    }

    function test_CreateAuction_RejectsReuse() public {
        auction.createAuction(bundleHash);

        vm.expectRevert(RideAuction.AuctionAlreadyExists.selector);
        auction.createAuction(bundleHash);
    }

    function test_CreateAuction_OnlyOwner() public {
        vm.prank(bidder1);
        vm.expectRevert(RideAuction.OnlyOwner.selector);
        auction.createAuction(bundleHash);
    }

    // =========================================================================
    // COMMIT PHASE TESTS
    // =========================================================================

    function test_CommitBid() public {
        auction.createAuction(bundleHash);

        uint256 quotedCost = 1 ether;
        bytes32 salt = keccak256("salt1");
        bytes32 commitHash = auction.computeCommitmentHash(bundleHash, bidder1, quotedCost, salt);

        vm.prank(bidder1);
        auction.commitBid(bundleHash, commitHash);

        (bytes32 hash, bool revealed,,) = auction.getCommitment(bundleHash, bidder1);
        assertEq(hash, commitHash);
        assertFalse(revealed);
    }

    function test_CommitBid_OnlyWhitelisted() public {
        auction.createAuction(bundleHash);

        vm.prank(nonBidder);
        vm.expectRevert(RideAuction.BidderNotWhitelisted.selector);
        auction.commitBid(bundleHash, bytes32(0));
    }

    function test_CommitBid_BeforeStart() public {
        // Not testing - commit starts immediately on creation
    }

    function test_CommitBid_AfterEnd() public {
        auction.createAuction(bundleHash);

        // Warp past commit phase
        vm.warp(block.timestamp + 301);

        vm.prank(bidder1);
        vm.expectRevert(RideAuction.CommitPhaseNotActive.selector);
        auction.commitBid(bundleHash, bytes32(0));
    }

    function test_CommitBid_AuctionDoesNotExist() public {
        bytes32 fakeBundleHash = keccak256("fake");

        vm.prank(bidder1);
        vm.expectRevert(RideAuction.AuctionDoesNotExist.selector);
        auction.commitBid(fakeBundleHash, bytes32(0));
    }

    function test_CommitBid_CanUpdateDuringCommitPhase() public {
        auction.createAuction(bundleHash);

        bytes32 commitHash1 = keccak256("commit1");
        bytes32 commitHash2 = keccak256("commit2");

        vm.prank(bidder1);
        auction.commitBid(bundleHash, commitHash1);

        vm.prank(bidder1);
        auction.commitBid(bundleHash, commitHash2);

        (bytes32 hash,,,) = auction.getCommitment(bundleHash, bidder1);
        assertEq(hash, commitHash2);
    }

    // =========================================================================
    // REVEAL PHASE TESTS
    // =========================================================================

    function test_RevealBid() public {
        auction.createAuction(bundleHash);

        uint256 quotedCost = 1 ether;
        bytes32 salt = keccak256("salt1");
        bytes32 commitHash = auction.computeCommitmentHash(bundleHash, bidder1, quotedCost, salt);

        vm.prank(bidder1);
        auction.commitBid(bundleHash, commitHash);

        // Warp to reveal phase
        vm.warp(block.timestamp + 301);

        vm.prank(bidder1);
        auction.revealBid(bundleHash, quotedCost, salt);

        (, bool revealed, uint256 revealedCost, uint256 revealOrder) = auction.getCommitment(bundleHash, bidder1);
        assertTrue(revealed);
        assertEq(revealedCost, quotedCost);
        assertEq(revealOrder, 1);
    }

    function test_RevealBid_InvalidHash() public {
        auction.createAuction(bundleHash);

        uint256 quotedCost = 1 ether;
        bytes32 salt = keccak256("salt1");
        bytes32 commitHash = auction.computeCommitmentHash(bundleHash, bidder1, quotedCost, salt);

        vm.prank(bidder1);
        auction.commitBid(bundleHash, commitHash);

        vm.warp(block.timestamp + 301);

        // Try to reveal with wrong cost
        vm.prank(bidder1);
        vm.expectRevert(RideAuction.InvalidCommitmentHash.selector);
        auction.revealBid(bundleHash, 2 ether, salt); // Wrong amount
    }

    function test_RevealBid_BeforeRevealPhase() public {
        auction.createAuction(bundleHash);

        uint256 quotedCost = 1 ether;
        bytes32 salt = keccak256("salt1");
        bytes32 commitHash = auction.computeCommitmentHash(bundleHash, bidder1, quotedCost, salt);

        vm.prank(bidder1);
        auction.commitBid(bundleHash, commitHash);

        // Still in commit phase
        vm.prank(bidder1);
        vm.expectRevert(RideAuction.RevealPhaseNotActive.selector);
        auction.revealBid(bundleHash, quotedCost, salt);
    }

    function test_RevealBid_AfterRevealPhase() public {
        auction.createAuction(bundleHash);

        uint256 quotedCost = 1 ether;
        bytes32 salt = keccak256("salt1");
        bytes32 commitHash = auction.computeCommitmentHash(bundleHash, bidder1, quotedCost, salt);

        vm.prank(bidder1);
        auction.commitBid(bundleHash, commitHash);

        // Warp past reveal phase
        vm.warp(block.timestamp + 421);

        vm.prank(bidder1);
        vm.expectRevert(RideAuction.RevealPhaseNotActive.selector);
        auction.revealBid(bundleHash, quotedCost, salt);
    }

    function test_RevealBid_AlreadyRevealed() public {
        auction.createAuction(bundleHash);

        uint256 quotedCost = 1 ether;
        bytes32 salt = keccak256("salt1");
        bytes32 commitHash = auction.computeCommitmentHash(bundleHash, bidder1, quotedCost, salt);

        vm.prank(bidder1);
        auction.commitBid(bundleHash, commitHash);

        vm.warp(block.timestamp + 301);

        vm.prank(bidder1);
        auction.revealBid(bundleHash, quotedCost, salt);

        vm.prank(bidder1);
        vm.expectRevert(RideAuction.BidAlreadyRevealed.selector);
        auction.revealBid(bundleHash, quotedCost, salt);
    }

    function test_RevealBid_NoCommitment() public {
        auction.createAuction(bundleHash);

        vm.warp(block.timestamp + 301);

        vm.prank(bidder1);
        vm.expectRevert(RideAuction.NoBidToReveal.selector);
        auction.revealBid(bundleHash, 1 ether, keccak256("salt"));
    }

    // =========================================================================
    // FINALIZATION TESTS
    // =========================================================================

    function test_FinalizeAuction_LowestWins() public {
        _setupThreeBidders();

        // _setupThreeBidders already warped to reveal phase (301)
        // Just warp 120 more seconds past reveal phase end
        vm.warp(block.timestamp + 120);

        auction.finalizeAuction(bundleHash);

        (,,,, address winner, uint256 winningBid,) = auction.getAuction(bundleHash);
        assertEq(winner, bidder2); // 0.5 ETH
        assertEq(winningBid, 0.5 ether);
    }

    function test_FinalizeAuction_TieBreakByRevealOrder() public {
        auction.createAuction(bundleHash);

        uint256 sameBid = 1 ether;

        // Bidder 1 and 2 both commit 1 ETH
        // Bidder 1 and 2 both commit 1 ETH
        bytes32 salt1 = keccak256("salt1");
        bytes32 salt2 = keccak256("salt2");

        bytes32 hash1 = auction.computeCommitmentHash(bundleHash, bidder1, sameBid, salt1);
        vm.prank(bidder1);
        auction.commitBid(bundleHash, hash1);

        bytes32 hash2 = auction.computeCommitmentHash(bundleHash, bidder2, sameBid, salt2);
        vm.prank(bidder2);
        auction.commitBid(bundleHash, hash2);

        // Warp to reveal phase
        vm.warp(block.timestamp + 301);

        // Bidder 2 reveals first
        vm.prank(bidder2);
        auction.revealBid(bundleHash, sameBid, salt2);

        // Bidder 1 reveals second
        vm.prank(bidder1);
        auction.revealBid(bundleHash, sameBid, salt1);

        // Finalize
        vm.warp(block.timestamp + 121);
        auction.finalizeAuction(bundleHash);

        (,,,, address winner,,) = auction.getAuction(bundleHash);
        assertEq(winner, bidder2); // Revealed first
    }

    function test_FinalizeAuction_Unsold() public {
        auction.createAuction(bundleHash);

        // Commit but don't reveal
        bytes32 salt = keccak256("salt");
        bytes32 hash = auction.computeCommitmentHash(bundleHash, bidder1, 1 ether, salt);
        vm.prank(bidder1);
        auction.commitBid(bundleHash, hash);

        // Warp past reveal phase
        vm.warp(block.timestamp + 421);

        auction.finalizeAuction(bundleHash);

        (,,,bool finalized, address winner,,) = auction.getAuction(bundleHash);
        assertTrue(finalized);
        assertEq(winner, address(0)); // Unsold
    }

    function test_FinalizeAuction_AlreadyFinalized() public {
        _setupThreeBidders();
        vm.warp(block.timestamp + 120); // Past reveal

        auction.finalizeAuction(bundleHash);

        vm.expectRevert(RideAuction.AuctionAlreadyFinalized.selector);
        auction.finalizeAuction(bundleHash);
    }

    function test_FinalizeAuction_NotReady() public {
        auction.createAuction(bundleHash);

        // Still in commit phase
        vm.expectRevert(RideAuction.AuctionNotReadyForFinalization.selector);
        auction.finalizeAuction(bundleHash);
    }

    function test_FinalizeAuction_EarlyIfAllRevealed() public {
        auction.createAuction(bundleHash);

        uint256 quotedCost = 1 ether;
        bytes32 salt = keccak256("salt");
        bytes32 hash = auction.computeCommitmentHash(bundleHash, bidder1, quotedCost, salt);

        vm.prank(bidder1);
        auction.commitBid(bundleHash, hash);

        // Only one bidder committed
        // Warp to reveal phase (not past it)
        vm.warp(block.timestamp + 301);

        vm.prank(bidder1);
        auction.revealBid(bundleHash, quotedCost, salt);

        // Should be able to finalize early since all committed bids revealed
        auction.finalizeAuction(bundleHash);

        (,,,bool finalized, address winner,,) = auction.getAuction(bundleHash);
        assertTrue(finalized);
        assertEq(winner, bidder1);
    }

    // =========================================================================
    // VIEW FUNCTION TESTS
    // =========================================================================

    function test_GetAuctionPhase() public {
        // Not started
        assertEq(auction.getAuctionPhase(bundleHash), 0);

        auction.createAuction(bundleHash);

        // Commit phase
        assertEq(auction.getAuctionPhase(bundleHash), 1);

        // Reveal phase
        vm.warp(block.timestamp + 301);
        assertEq(auction.getAuctionPhase(bundleHash), 2);

        // Expired
        vm.warp(block.timestamp + 121);
        assertEq(auction.getAuctionPhase(bundleHash), 4);

        // Finalized
        auction.finalizeAuction(bundleHash);
        assertEq(auction.getAuctionPhase(bundleHash), 3);
    }

    // =========================================================================
    // HELPER FUNCTIONS
    // =========================================================================

    function _setupThreeBidders() internal {
        auction.createAuction(bundleHash);

        // Verify whitelisting
        if (!auction.isBidderWhitelisted(bidder1)) console.log("ERROR: Bidder 1 not whitelisted");
        if (!auction.isBidderWhitelisted(bidder2)) console.log("ERROR: Bidder 2 not whitelisted");
        if (!auction.isBidderWhitelisted(bidder3)) console.log("ERROR: Bidder 3 not whitelisted");

        // Bidder 1: 1 ETH
        bytes32 hash1 = auction.computeCommitmentHash(bundleHash, bidder1, 1 ether, keccak256("s1"));
        vm.prank(bidder1);
        auction.commitBid(bundleHash, hash1);

        // Bidder 2: 0.5 ETH (lowest)
        bytes32 hash2 = auction.computeCommitmentHash(bundleHash, bidder2, 0.5 ether, keccak256("s2"));
        vm.prank(bidder2);
        auction.commitBid(bundleHash, hash2);

        // Bidder 3: 2 ETH
        bytes32 hash3 = auction.computeCommitmentHash(bundleHash, bidder3, 2 ether, keccak256("s3"));
        vm.prank(bidder3);
        auction.commitBid(bundleHash, hash3);

        // Warp to reveal phase
        vm.warp(block.timestamp + 301);

        // All reveal
        vm.prank(bidder1);
        auction.revealBid(bundleHash, 1 ether, keccak256("s1"));

        vm.prank(bidder2);
        auction.revealBid(bundleHash, 0.5 ether, keccak256("s2"));

        vm.prank(bidder3);
        auction.revealBid(bundleHash, 2 ether, keccak256("s3"));
    }
}
