// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {RideAuction} from "../src/RideAuction.sol";
import {PaymentExecutor} from "../src/PaymentExecutor.sol";

/**
 * @title AuctionLifecycle
 * @notice Simulates a complete auction lifecycle for testing/demo
 */
contract AuctionLifecycle is Script {
    // Constants for anvil accounts
    uint256 constant DEPLOYER_KEY = 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80;
    uint256 constant BIDDER1_KEY = 0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d;
    uint256 constant BIDDER2_KEY = 0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a;

    function run() external {
        address bidder1 = vm.addr(BIDDER1_KEY);
        address bidder2 = vm.addr(BIDDER2_KEY);

        // Deploy
        vm.startBroadcast(DEPLOYER_KEY);
        
        RideAuction auction = new RideAuction();
        PaymentExecutor executor = new PaymentExecutor();
        
        executor.setRideAuction(address(auction));
        auction.addBidder(bidder1);
        auction.addBidder(bidder2);
        executor.authorizeRecorder(vm.addr(DEPLOYER_KEY));

        bytes32 bundleHash = keccak256("bundle_001");
        auction.createAuction(bundleHash);
        
        vm.stopBroadcast();
        console.log("Deployed and auction created");

        // Commit phase
        bytes32 salt1 = keccak256("s1");
        bytes32 salt2 = keccak256("s2");
        uint256 bid1 = 0.5 ether;
        uint256 bid2 = 0.45 ether;

        bytes32 hash1 = _computeHash(auction, bundleHash, bidder1, bid1, salt1);
        bytes32 hash2 = _computeHash(auction, bundleHash, bidder2, bid2, salt2);

        vm.broadcast(BIDDER1_KEY);
        auction.commitBid(bundleHash, hash1);

        vm.broadcast(BIDDER2_KEY);
        auction.commitBid(bundleHash, hash2);
        console.log("Commits done");

        // Reveal phase
        vm.warp(block.timestamp + 301);

        vm.broadcast(BIDDER1_KEY);
        auction.revealBid(bundleHash, bid1, salt1);

        vm.broadcast(BIDDER2_KEY);
        auction.revealBid(bundleHash, bid2, salt2);
        console.log("Reveals done");

        // Finalize
        vm.startBroadcast(DEPLOYER_KEY);
        auction.finalizeAuction(bundleHash);

        (,,,,address winner, uint256 winningBid,) = auction.getAuction(bundleHash);
        console.log("Winner:", winner);

        executor.recordPayment(bundleHash, winner, winningBid, keccak256("tx"));
        vm.stopBroadcast();
        
        console.log("Complete!");
    }

    function _computeHash(
        RideAuction auction,
        bytes32 bundleHash,
        address bidder,
        uint256 cost,
        bytes32 salt
    ) internal view returns (bytes32) {
        return auction.computeCommitmentHash(bundleHash, bidder, cost, salt);
    }
}
