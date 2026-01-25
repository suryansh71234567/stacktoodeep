// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {RideAuction} from "../src/RideAuction.sol";
import {PaymentExecutor} from "../src/PaymentExecutor.sol";

/**
 * @title Deploy
 * @notice Deployment script for RideAuction and PaymentExecutor contracts
 * @dev Run with: forge script script/Deploy.s.sol --rpc-url <RPC_URL> --broadcast
 */
contract Deploy is Script {
    function run() external returns (RideAuction rideAuction, PaymentExecutor paymentExecutor) {
        // Get deployer private key from environment
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console.log("Deployer address:", deployer);
        console.log("Deployer balance:", deployer.balance);

        vm.startBroadcast(deployerPrivateKey);

        // Deploy RideAuction
        rideAuction = new RideAuction();
        console.log("RideAuction deployed at:", address(rideAuction));

        // Deploy PaymentExecutor
        paymentExecutor = new PaymentExecutor();
        console.log("PaymentExecutor deployed at:", address(paymentExecutor));

        // Link PaymentExecutor to RideAuction
        paymentExecutor.setRideAuction(address(rideAuction));
        console.log("PaymentExecutor linked to RideAuction");

        vm.stopBroadcast();

        // Log deployment summary
        console.log("");
        console.log("=== DEPLOYMENT SUMMARY ===");
        console.log("RideAuction:", address(rideAuction));
        console.log("PaymentExecutor:", address(paymentExecutor));
        console.log("Owner:", deployer);
        console.log("==========================");

        return (rideAuction, paymentExecutor);
    }
}

/**
 * @title DeployLocal
 * @notice Simplified deployment for local testing (no private key needed)
 * @dev Run with: forge script script/Deploy.s.sol:DeployLocal --fork-url http://localhost:8545
 */
contract DeployLocal is Script {
    function run() external returns (RideAuction rideAuction, PaymentExecutor paymentExecutor) {
        // Use first anvil account
        vm.startBroadcast();

        // Deploy RideAuction
        rideAuction = new RideAuction();
        console.log("RideAuction deployed at:", address(rideAuction));

        // Deploy PaymentExecutor
        paymentExecutor = new PaymentExecutor();
        console.log("PaymentExecutor deployed at:", address(paymentExecutor));

        // Link PaymentExecutor to RideAuction
        paymentExecutor.setRideAuction(address(rideAuction));

        vm.stopBroadcast();

        return (rideAuction, paymentExecutor);
    }
}
