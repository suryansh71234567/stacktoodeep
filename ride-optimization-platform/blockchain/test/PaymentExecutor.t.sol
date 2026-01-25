// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {PaymentExecutor} from "../src/PaymentExecutor.sol";
import {RideAuction} from "../src/RideAuction.sol";

/**
 * @title PaymentExecutorTest
 * @notice Comprehensive tests for PaymentExecutor contract
 */
contract PaymentExecutorTest is Test {
    PaymentExecutor public executor;
    RideAuction public auction;

    address public owner = address(this);
    address public recorder = address(0x1);
    address public nonRecorder = address(0x2);
    address public winner = address(0x3);

    bytes32 public bundleHash = keccak256("bundle_001");
    bytes32 public txHash = keccak256("tx_001");

    function setUp() public {
        executor = new PaymentExecutor();
        auction = new RideAuction();

        // Link to auction
        executor.setRideAuction(address(auction));

        // Authorize recorder
        executor.authorizeRecorder(recorder);
    }

    // =========================================================================
    // ADMIN TESTS
    // =========================================================================

    function test_OwnerIsDeployer() public view {
        assertEq(executor.owner(), owner);
    }

    function test_SetRideAuction() public {
        address newAuction = address(0x100);
        executor.setRideAuction(newAuction);
        assertEq(executor.rideAuction(), newAuction);
    }

    function test_SetRideAuction_OnlyOwner() public {
        vm.prank(recorder);
        vm.expectRevert(PaymentExecutor.OnlyOwner.selector);
        executor.setRideAuction(address(0x100));
    }

    function test_AuthorizeRecorder() public {
        address newRecorder = address(0x200);
        executor.authorizeRecorder(newRecorder);
        assertTrue(executor.isAuthorizedRecorder(newRecorder));
    }

    function test_RevokeRecorder() public {
        executor.revokeRecorder(recorder);
        assertFalse(executor.isAuthorizedRecorder(recorder));
    }

    function test_TransferOwnership() public {
        address newOwner = address(0x300);
        executor.transferOwnership(newOwner);
        assertEq(executor.owner(), newOwner);
    }

    // =========================================================================
    // PAYMENT RECORDING TESTS
    // =========================================================================

    function test_RecordPayment() public {
        uint256 amount = 1 ether;

        vm.prank(recorder);
        executor.recordPayment(bundleHash, winner, amount, txHash);

        (
            address recordedWinner,
            uint256 recordedAmount,
            bytes32 recordedTxHash,
            uint256 timestamp,
            bool recorded
        ) = executor.getPayment(bundleHash);

        assertEq(recordedWinner, winner);
        assertEq(recordedAmount, amount);
        assertEq(recordedTxHash, txHash);
        assertEq(timestamp, block.timestamp);
        assertTrue(recorded);
    }

    function test_RecordPayment_EmitsEvent() public {
        uint256 amount = 1 ether;

        vm.prank(recorder);
        vm.expectEmit(true, true, false, true);
        emit PaymentExecutor.PaymentExecuted(bundleHash, winner, amount, txHash);
        executor.recordPayment(bundleHash, winner, amount, txHash);
    }

    function test_RecordPayment_OnlyAuthorizedRecorder() public {
        vm.prank(nonRecorder);
        vm.expectRevert(PaymentExecutor.OnlyAuthorizedRecorder.selector);
        executor.recordPayment(bundleHash, winner, 1 ether, txHash);
    }

    function test_RecordPayment_InvalidWinner() public {
        vm.prank(recorder);
        vm.expectRevert(PaymentExecutor.InvalidWinner.selector);
        executor.recordPayment(bundleHash, address(0), 1 ether, txHash);
    }

    function test_RecordPayment_InvalidAmount() public {
        vm.prank(recorder);
        vm.expectRevert(PaymentExecutor.InvalidAmount.selector);
        executor.recordPayment(bundleHash, winner, 0, txHash);
    }

    function test_RecordPayment_AlreadyRecorded() public {
        vm.prank(recorder);
        executor.recordPayment(bundleHash, winner, 1 ether, txHash);

        vm.prank(recorder);
        vm.expectRevert(PaymentExecutor.PaymentAlreadyRecorded.selector);
        executor.recordPayment(bundleHash, winner, 1 ether, txHash);
    }

    // =========================================================================
    // VIEW FUNCTION TESTS
    // =========================================================================

    function test_IsPaymentRecorded() public {
        assertFalse(executor.isPaymentRecorded(bundleHash));

        vm.prank(recorder);
        executor.recordPayment(bundleHash, winner, 1 ether, txHash);

        assertTrue(executor.isPaymentRecorded(bundleHash));
    }

    function test_IsAuthorizedRecorder() public {
        assertTrue(executor.isAuthorizedRecorder(recorder));
        assertFalse(executor.isAuthorizedRecorder(nonRecorder));
    }

    // =========================================================================
    // MULTIPLE PAYMENTS TEST
    // =========================================================================

    function test_RecordMultiplePayments() public {
        bytes32 bundleHash1 = keccak256("bundle_1");
        bytes32 bundleHash2 = keccak256("bundle_2");
        bytes32 bundleHash3 = keccak256("bundle_3");

        vm.startPrank(recorder);
        executor.recordPayment(bundleHash1, winner, 1 ether, keccak256("tx1"));
        executor.recordPayment(bundleHash2, winner, 2 ether, keccak256("tx2"));
        executor.recordPayment(bundleHash3, winner, 0.5 ether, keccak256("tx3"));
        vm.stopPrank();

        assertTrue(executor.isPaymentRecorded(bundleHash1));
        assertTrue(executor.isPaymentRecorded(bundleHash2));
        assertTrue(executor.isPaymentRecorded(bundleHash3));

        (, uint256 amount1,,,) = executor.getPayment(bundleHash1);
        (, uint256 amount2,,,) = executor.getPayment(bundleHash2);
        (, uint256 amount3,,,) = executor.getPayment(bundleHash3);

        assertEq(amount1, 1 ether);
        assertEq(amount2, 2 ether);
        assertEq(amount3, 0.5 ether);
    }
}
