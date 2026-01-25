// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {RideAuction} from "../src/RideAuction.sol";
import {PaymentExecutor} from "../src/PaymentExecutor.sol";

/**
 * @title IntegrationTest
 * @notice End-to-end integration tests for the auction system
 */
contract IntegrationTest is Test {
    RideAuction public auction;
    PaymentExecutor public executor;

    address public owner = address(this);
    address public bidder1 = address(0x1);
    address public bidder2 = address(0x2);
    address public bidder3 = address(0x3);
    address public agentAI = address(0xA1);

    bytes32 public bundleHash = keccak256("bundle_integration_001");

    function setUp() public {
        // Deploy contracts
        auction = new RideAuction();
        executor = new PaymentExecutor();

        // Link executor to auction
        executor.setRideAuction(address(auction));

        // Whitelist bidders (companies)
        auction.addBidder(bidder1); // Uber
        auction.addBidder(bidder2); // Ola
        auction.addBidder(bidder3); // Rapido

        // Authorize AI agent to record payments
        executor.authorizeRecorder(agentAI);
    }

    // =========================================================================
    // FULL LIFECYCLE TEST
    // =========================================================================

    function test_FullAuctionLifecycle() public {
        // ===== PHASE 0: Backend creates auction =====
        console.log("PHASE 0: Backend creates auction");
        auction.createAuction(bundleHash);

        uint8 phase = auction.getAuctionPhase(bundleHash);
        assertEq(phase, 1); // Commit phase
        console.log("Auction created, phase:", phase);

        // ===== PHASE 1: Companies commit bids =====
        console.log("PHASE 1: Companies commit bids");

        // Uber bids 0.8 ETH
        uint256 uberBid = 0.8 ether;
        bytes32 uberSalt = keccak256("uber_secret_salt");
        bytes32 uberCommit = auction.computeCommitmentHash(bundleHash, bidder1, uberBid, uberSalt);

        // Ola bids 0.6 ETH (lowest)
        uint256 olaBid = 0.6 ether;
        bytes32 olaSalt = keccak256("ola_secret_salt");
        bytes32 olaCommit = auction.computeCommitmentHash(bundleHash, bidder2, olaBid, olaSalt);

        // Rapido bids 0.7 ETH
        uint256 rapidoBid = 0.7 ether;
        bytes32 rapidoSalt = keccak256("rapido_secret_salt");
        bytes32 rapidoCommit = auction.computeCommitmentHash(bundleHash, bidder3, rapidoBid, rapidoSalt);

        vm.prank(bidder1);
        auction.commitBid(bundleHash, uberCommit);
        console.log("Uber committed");

        vm.prank(bidder2);
        auction.commitBid(bundleHash, olaCommit);
        console.log("Ola committed");

        vm.prank(bidder3);
        auction.commitBid(bundleHash, rapidoCommit);
        console.log("Rapido committed");

        // Verify bid count
        (,,,,,, uint256 bidCount) = auction.getAuction(bundleHash);
        assertEq(bidCount, 3);

        // ===== PHASE 2: Time advances to reveal phase =====
        console.log("PHASE 2: Advancing to reveal phase");
        vm.warp(block.timestamp + 301); // 5 min + 1 sec

        phase = auction.getAuctionPhase(bundleHash);
        assertEq(phase, 2); // Reveal phase
        console.log("Now in reveal phase");

        // ===== PHASE 3: Companies reveal bids =====
        console.log("PHASE 3: Companies reveal bids");

        vm.prank(bidder3);
        auction.revealBid(bundleHash, rapidoBid, rapidoSalt);
        console.log("Rapido revealed: 0.7 ETH");

        vm.prank(bidder2);
        auction.revealBid(bundleHash, olaBid, olaSalt);
        console.log("Ola revealed: 0.6 ETH");

        vm.prank(bidder1);
        auction.revealBid(bundleHash, uberBid, uberSalt);
        console.log("Uber revealed: 0.8 ETH");

        // Verify reveals
        (, bool uberRevealed,,) = auction.getCommitment(bundleHash, bidder1);
        (, bool olaRevealed,,) = auction.getCommitment(bundleHash, bidder2);
        (, bool rapidoRevealed,,) = auction.getCommitment(bundleHash, bidder3);

        assertTrue(uberRevealed);
        assertTrue(olaRevealed);
        assertTrue(rapidoRevealed);

        // ===== PHASE 4: Finalize auction =====
        console.log("PHASE 4: Finalizing auction");
        auction.finalizeAuction(bundleHash);

        (,,,bool finalized, address winner, uint256 winningBid,) = auction.getAuction(bundleHash);

        assertTrue(finalized);
        assertEq(winner, bidder2); // Ola wins
        assertEq(winningBid, 0.6 ether);
        console.log("Winner: Ola (bidder2)");
        console.log("Winning bid:", winningBid);

        // ===== PHASE 5: AI agent executes payment and records =====
        console.log("PHASE 5: AI agent records payment");

        bytes32 paymentTxHash = keccak256("0xpayment_tx_hash_from_x402");

        vm.prank(agentAI);
        executor.recordPayment(bundleHash, winner, winningBid, paymentTxHash);

        // Verify payment record
        (
            address recordedWinner,
            uint256 recordedAmount,
            bytes32 recordedTxHash,
            ,
            bool recorded
        ) = executor.getPayment(bundleHash);

        assertTrue(recorded);
        assertEq(recordedWinner, bidder2);
        assertEq(recordedAmount, 0.6 ether);
        assertEq(recordedTxHash, paymentTxHash);

        console.log("Payment recorded successfully!");
        console.log("=== AUCTION LIFECYCLE COMPLETE ===");
    }

    // =========================================================================
    // SCENARIO TESTS
    // =========================================================================

    function test_Scenario_OneBidder() public {
        auction.createAuction(bundleHash);

        // Only one bidder
        uint256 bid = 1 ether;
        bytes32 salt = keccak256("solo");
        bytes32 commit = auction.computeCommitmentHash(bundleHash, bidder1, bid, salt);

        vm.prank(bidder1);
        auction.commitBid(bundleHash, commit);

        vm.warp(block.timestamp + 301);

        vm.prank(bidder1);
        auction.revealBid(bundleHash, bid, salt);

        auction.finalizeAuction(bundleHash);

        (,,,, address winner, uint256 winningBid,) = auction.getAuction(bundleHash);
        assertEq(winner, bidder1);
        assertEq(winningBid, 1 ether);
    }

    function test_Scenario_NoBidsRevealed() public {
        auction.createAuction(bundleHash);

        // Bidder commits but doesn't reveal
        bytes32 commit = keccak256("hidden_bid");
        vm.prank(bidder1);
        auction.commitBid(bundleHash, commit);

        // Skip through both phases
        vm.warp(block.timestamp + 421);

        auction.finalizeAuction(bundleHash);

        (,,,bool finalized, address winner,,) = auction.getAuction(bundleHash);
        assertTrue(finalized);
        assertEq(winner, address(0)); // Unsold
    }

    function test_Scenario_PartialReveals() public {
        auction.createAuction(bundleHash);

        // Two bidders commit
        uint256 bid1 = 1 ether;
        uint256 bid2 = 0.5 ether;
        bytes32 salt1 = keccak256("s1");
        bytes32 salt2 = keccak256("s2");

        // Bidder 1
        bytes32 hash1 = auction.computeCommitmentHash(bundleHash, bidder1, bid1, salt1);
        vm.prank(bidder1);
        auction.commitBid(bundleHash, hash1);

        // Bidder 2
        bytes32 hash2 = auction.computeCommitmentHash(bundleHash, bidder2, bid2, salt2);
        vm.prank(bidder2);
        auction.commitBid(bundleHash, hash2);

        vm.warp(block.timestamp + 301);

        // Only bidder2 reveals
        vm.prank(bidder2);
        auction.revealBid(bundleHash, bid2, salt2);

        // Warp past reveal and finalize
        vm.warp(block.timestamp + 121);
        auction.finalizeAuction(bundleHash);

        (,,,, address winner, uint256 winningBid,) = auction.getAuction(bundleHash);
        assertEq(winner, bidder2); // Only one who revealed
        assertEq(winningBid, 0.5 ether);
    }

    function test_Scenario_EarlyFinalization() public {
        auction.createAuction(bundleHash);

        // Single bidder
        uint256 bid = 0.75 ether;
        bytes32 salt = keccak256("early");

        bytes32 hash = auction.computeCommitmentHash(bundleHash, bidder1, bid, salt);
        vm.prank(bidder1);
        auction.commitBid(bundleHash, hash);

        vm.warp(block.timestamp + 301);

        vm.prank(bidder1);
        auction.revealBid(bundleHash, bid, salt);

        // Can finalize early since all committed bidders revealed
        // Note: Still in reveal phase (not expired yet)
        auction.finalizeAuction(bundleHash);

        (,,,bool finalized, address winner,,) = auction.getAuction(bundleHash);
        assertTrue(finalized);
        assertEq(winner, bidder1);
    }

    function test_Scenario_MultipleBundlesSimultaneously() public {
        bytes32 bundle1 = keccak256("bundle_a");
        bytes32 bundle2 = keccak256("bundle_b");
        bytes32 bundle3 = keccak256("bundle_c");

        // Create three auctions
        auction.createAuction(bundle1);
        auction.createAuction(bundle2);
        auction.createAuction(bundle3);

        // All should be in commit phase
        assertEq(auction.getAuctionPhase(bundle1), 1);
        assertEq(auction.getAuctionPhase(bundle2), 1);
        assertEq(auction.getAuctionPhase(bundle3), 1);

        // Each bundle can have different bids
        vm.prank(bidder1);
        auction.commitBid(bundle1, keccak256("b1bid1"));

        vm.prank(bidder2);
        auction.commitBid(bundle2, keccak256("b2bid2"));

        vm.prank(bidder3);
        auction.commitBid(bundle3, keccak256("b3bid3"));

        // Verify independence
        (,,,,,, uint256 count1) = auction.getAuction(bundle1);
        (,,,,,, uint256 count2) = auction.getAuction(bundle2);
        (,,,,,, uint256 count3) = auction.getAuction(bundle3);

        assertEq(count1, 1);
        assertEq(count2, 1);
        assertEq(count3, 1);
    }

    // =========================================================================
    // SECURITY TESTS
    // =========================================================================

    function test_Security_BundleHashReuse() public {
        auction.createAuction(bundleHash);

        // Complete the auction
        vm.warp(block.timestamp + 421);
        auction.finalizeAuction(bundleHash);

        // Try to reuse the same bundleHash
        vm.expectRevert(RideAuction.AuctionAlreadyExists.selector);
        auction.createAuction(bundleHash);
    }

    function test_Security_UnauthorizedPaymentRecording() public {
        vm.prank(bidder1); // Not authorized
        vm.expectRevert(PaymentExecutor.OnlyAuthorizedRecorder.selector);
        executor.recordPayment(bundleHash, bidder1, 1 ether, keccak256("tx"));
    }

    function test_Security_BidTampering() public {
        auction.createAuction(bundleHash);

        uint256 realBid = 1 ether;
        bytes32 salt = keccak256("mysalt");

        bytes32 hash = auction.computeCommitmentHash(bundleHash, bidder1, realBid, salt);
        vm.prank(bidder1);
        auction.commitBid(bundleHash, hash);

        vm.warp(block.timestamp + 301);

        // Try to reveal a different (lower) bid
        vm.prank(bidder1);
        vm.expectRevert(RideAuction.InvalidCommitmentHash.selector);
        auction.revealBid(bundleHash, 0.5 ether, salt); // Trying to cheat

        // Can still reveal with correct bid
        vm.prank(bidder1);
        auction.revealBid(bundleHash, realBid, salt);

        (, bool revealed, uint256 revealedCost,) = auction.getCommitment(bundleHash, bidder1);
        assertTrue(revealed);
        assertEq(revealedCost, realBid);
    }

    // =========================================================================
    // EVENT TESTS
    // =========================================================================

    function test_Events_FullLifecycle() public {
        // Test AuctionCreated
        vm.expectEmit(true, false, false, true);
        emit RideAuction.AuctionCreated(bundleHash, block.timestamp + 300, block.timestamp + 420);
        auction.createAuction(bundleHash);

        // Test BidCommitted
        bytes32 commit = keccak256("commit");
        vm.prank(bidder1);
        vm.expectEmit(true, true, false, false);
        emit RideAuction.BidCommitted(bundleHash, bidder1);
        auction.commitBid(bundleHash, commit);

        // Setup for reveal
        bytes32 salt = keccak256("salt");
        uint256 bid = 1 ether;

        bytes32 hash2 = auction.computeCommitmentHash(bundleHash, bidder2, bid, salt);
        vm.prank(bidder2);
        auction.commitBid(bundleHash, hash2);

        vm.warp(block.timestamp + 301);

        // Test BidRevealed
        vm.prank(bidder2);
        vm.expectEmit(true, true, false, true);
        emit RideAuction.BidRevealed(bundleHash, bidder2, bid);
        auction.revealBid(bundleHash, bid, salt);

        // Test AuctionFinalized
        vm.warp(block.timestamp + 121);
        vm.expectEmit(true, true, false, true);
        emit RideAuction.AuctionFinalized(bundleHash, bidder2, bid);
        auction.finalizeAuction(bundleHash);

        // Test PaymentExecuted
        vm.prank(agentAI);
        vm.expectEmit(true, true, false, true);
        emit PaymentExecutor.PaymentExecuted(bundleHash, bidder2, bid, keccak256("tx"));
        executor.recordPayment(bundleHash, bidder2, bid, keccak256("tx"));
    }
}
