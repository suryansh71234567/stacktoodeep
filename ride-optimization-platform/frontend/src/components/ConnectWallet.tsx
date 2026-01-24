import { useState, useEffect } from 'react';

export default function ConnectWallet({ onConnect }: { onConnect: (address: string) => void }) {
  const [walletAddress, setWalletAddress] = useState("");

  const connectWallet = async () => {
    if (typeof window !== "undefined" && (window as any).ethereum) {
      try {
        // Request wallet connection
        const accounts = await (window as any).ethereum.request({ 
          method: "eth_requestAccounts" 
        });
        
        const account = accounts[0];
        setWalletAddress(account);
        onConnect(account); // Send address to parent
      } catch (error) {
        console.error("Connection failed", error);
      }
    } else {
      alert("Please install MetaMask!");
    }
  };

  return (
    <button
      onClick={connectWallet}
      className={`px-4 py-2 rounded-lg font-bold transition-all border ${
        walletAddress 
          ? "bg-green-900/50 border-green-500 text-green-400" 
          : "bg-yellow-500 hover:bg-yellow-400 text-black border-yellow-500"
      }`}
    >
      {walletAddress 
        ? `🟢 ${walletAddress.slice(0, 6)}...${walletAddress.slice(-4)}`
        : "🦊 Connect Wallet"
      }
    </button>
  );
}