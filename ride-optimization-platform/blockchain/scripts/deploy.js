/**
 * Deploy RideAuction and PaymentExecutor with pre-whitelisted companies.
 * 
 * Usage: npx hardhat run scripts/deploy.js --network localhost
 * 
 * This script:
 * 1. Deploys RideAuction contract
 * 2. Deploys PaymentExecutor contract
 * 3. Links PaymentExecutor to RideAuction
 * 4. Whitelists all demo companies as bidders
 * 5. Authorizes admin as payment recorder
 */

const hre = require("hardhat");

// Demo companies to be whitelisted as bidders
// These are Hardhat's default test accounts #1-4
const DEMO_COMPANIES = [
  {
    name: "RideShare Alpha",
    address: "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
  },
  {
    name: "QuickCab Beta",
    address: "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"
  },
  {
    name: "MetroRides Gamma",
    address: "0x90F79bf6EB2c4f870365E785982E1f101E93b906"
  },
  {
    name: "CityWheels Delta",
    address: "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65"
  }
];

async function main() {
  const [deployer] = await hre.ethers.getSigners();

  console.log("=".repeat(60));
  console.log("DEPLOYING AUCTION CONTRACTS");
  console.log("=".repeat(60));
  console.log(`Deployer: ${deployer.address}`);
  console.log("");

  // 1. Deploy RideAuction
  console.log("--- Deploying RideAuction ---");
  const RideAuction = await hre.ethers.getContractFactory("src/RideAuction.sol:RideAuction");
  const rideAuction = await RideAuction.deploy();
  await rideAuction.waitForDeployment();
  const auctionAddress = await rideAuction.getAddress();
  console.log(`RideAuction deployed to: ${auctionAddress}`);

  // 2. Deploy PaymentExecutor
  console.log("\n--- Deploying PaymentExecutor ---");
  const PaymentExecutor = await hre.ethers.getContractFactory("src/PaymentExecutor.sol:PaymentExecutor");
  const paymentExecutor = await PaymentExecutor.deploy();
  await paymentExecutor.waitForDeployment();
  const paymentAddress = await paymentExecutor.getAddress();
  console.log(`PaymentExecutor deployed to: ${paymentAddress}`);

  // 3. Link PaymentExecutor to RideAuction
  console.log("\n--- Linking Contracts ---");
  await paymentExecutor.setRideAuction(auctionAddress);
  console.log(`PaymentExecutor linked to RideAuction`);

  // 4. Whitelist all demo companies
  console.log("\n--- Whitelisting Companies as Bidders ---");
  for (const company of DEMO_COMPANIES) {
    await rideAuction.addBidder(company.address);
    console.log(`[OK] ${company.name}: ${company.address}`);
  }

  // 5. Authorize deployer as payment recorder (for AI agent simulation)
  console.log("\n--- Authorizing Payment Recorder ---");
  await paymentExecutor.authorizeRecorder(deployer.address);
  console.log(`[OK] Authorized: ${deployer.address}`);

  // Print summary
  console.log("\n" + "=".repeat(60));
  console.log("DEPLOYMENT COMPLETE");
  console.log("=".repeat(60));
  console.log("\nAdd these to your .env file:\n");
  console.log(`RIDE_AUCTION_ADDRESS=${auctionAddress}`);
  console.log(`PAYMENT_EXECUTOR_ADDRESS=${paymentAddress}`);
  console.log(`ADMIN_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80`);
  console.log(`BLOCKCHAIN_RPC_URL=http://localhost:8545`);
  console.log("\n" + "=".repeat(60));
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });