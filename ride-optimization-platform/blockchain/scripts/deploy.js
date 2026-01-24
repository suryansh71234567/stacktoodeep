const hre = require("hardhat");

async function main() {
  const RideAuction = await hre.ethers.getContractFactory("RideAuction");
  
  console.log("Deploying RideAuction...");
  const rideAuction = await RideAuction.deploy();
  await rideAuction.waitForDeployment();

  console.log("RideAuction deployed to:", rideAuction.target);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});