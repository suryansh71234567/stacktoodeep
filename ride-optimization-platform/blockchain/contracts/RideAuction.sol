// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract RideAuction {
    struct Auction {
        uint256 maxPrice;     // In WEI
        uint256 lowestBid;    // In WEI
        address winner;
        bool ended;
        mapping(address => bytes32) commitments; // Stores Hash(Price + Salt)
    }

    mapping(uint256 => Auction) public auctions;
    uint256 public auctionCounter;

    event AuctionStarted(uint256 auctionId, uint256 maxPrice);
    event WinnerSelected(uint256 auctionId, address driver, uint256 amount);

    // 1. Backend starts auction & deposits ETH safety fund
    function createAuction(uint256 _maxPrice) public payable {
        require(msg.value >= _maxPrice, "Deposit ETH to cover max price");
        
        auctionCounter++;
        Auction storage a = auctions[auctionCounter];
        a.maxPrice = _maxPrice;
        a.lowestBid = _maxPrice;
        a.ended = false;

        emit AuctionStarted(auctionCounter, _maxPrice);
    }

    // 2. Drivers Commit (Hide their price)
    function commitBid(uint256 _auctionId, bytes32 _commitment) public {
        require(!auctions[_auctionId].ended, "Auction ended");
        auctions[_auctionId].commitments[msg.sender] = _commitment;
    }

    // 3. Drivers Reveal (Show price & salt)
    // In a real app, this happens after a timer. For hackathon, we call it directly.
    function revealBid(uint256 _auctionId, uint256 _price, string memory _salt) public {
        Auction storage a = auctions[_auctionId];
        require(!a.ended, "Auction ended");

        // Verify Hash: keccak256(price + salt) must match commitment
        bytes32 proof = keccak256(abi.encodePacked(_price, _salt));
        require(a.commitments[msg.sender] == proof, "Invalid proof");

        // Check if this is the new lowest bid
        if (_price < a.lowestBid) {
            a.lowestBid = _price;
            a.winner = msg.sender;
        }
    }

    // 4. Backend Finalizes & Pays ETH (The x402 Protocol Step)
    function finalizeAuction(uint256 _auctionId) public {
        Auction storage a = auctions[_auctionId];
        require(!a.ended, "Already ended");
        require(a.winner != address(0), "No valid bids");

        a.ended = true;

        // PAY THE WINNER (ETH Transfer)
        payable(a.winner).transfer(a.lowestBid);

        // Refund the difference to Backend
        uint256 refund = a.maxPrice - a.lowestBid;
        if (refund > 0) {
            payable(msg.sender).transfer(refund);
        }

        emit WinnerSelected(_auctionId, a.winner, a.lowestBid);
    }
}