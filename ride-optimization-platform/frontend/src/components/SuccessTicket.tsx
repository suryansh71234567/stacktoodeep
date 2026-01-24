import React from 'react';
import { motion } from 'framer-motion';
import { QrCode, Car, Star, Wallet } from 'lucide-react';

// Define the shape of data we expect from the Backend
type BackendData = {
  driver_name: string;
  vehicle: string;
  savings: number;
  coupon_code: string;
  negotiated_price: number;
};

// Define the props for this component
type TicketProps = {
  onClose: () => void;
  data?: BackendData;      // Optional data (in case backend fails)
  walletAddress?: string;  // Optional wallet address
};

export default function SuccessTicket({ onClose, data, walletAddress }: TicketProps) {
  
  // 1. Safe defaults if data is missing (prevents crashes)
  const info = data || {
    driver_name: "Searching...",
    vehicle: "Unknown Vehicle",
    savings: 0,
    coupon_code: "WAIT-...",
    negotiated_price: 0
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <motion.div 
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="bg-slate-900 w-full max-w-sm rounded-3xl overflow-hidden border border-yellow-400/30 shadow-2xl relative"
      >
        {/* Confetti / Glow Effect */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-32 bg-yellow-400/20 rounded-full blur-[50px] pointer-events-none"></div>

        {/* 1. Header: Driver Found */}
        <div className="bg-yellow-400 p-6 text-center">
          <div className="w-16 h-16 bg-white rounded-full mx-auto flex items-center justify-center mb-3 shadow-lg">
             <Car size={32} className="text-black" />
          </div>
          <h2 className="text-2xl font-black text-black uppercase tracking-tight">Ride Confirmed!</h2>
          <p className="text-black/80 font-bold text-sm">
            You saved <span className="text-black font-black text-lg">₹{info.savings}</span> on this ride
          </p>
        </div>

        {/* 2. Ticket Details */}
        <div className="p-6 space-y-6 relative">
          {/* Jagged Line Effect */}
          <div className="absolute top-0 left-0 w-full h-4 -mt-2 bg-slate-900" style={{clipPath: "polygon(0 0, 5% 100%, 10% 0, 15% 100%, 20% 0, 25% 100%, 30% 0, 35% 100%, 40% 0, 45% 100%, 50% 0, 55% 100%, 60% 0, 65% 100%, 70% 0, 75% 100%, 80% 0, 85% 100%, 90% 0, 95% 100%, 100% 0)"}}></div>

          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div>
              <p className="text-xs text-slate-400 uppercase font-bold">Driver</p>
              <p className="text-lg font-bold text-white truncate max-w-[120px]">{info.driver_name}</p>
              <div className="flex items-center gap-1 text-yellow-400 text-xs">
                <Star size={10} fill="currentColor" /> 4.8 Rating
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-400 uppercase font-bold">Vehicle</p>
              <p className="text-white font-medium">{info.vehicle}</p>
              <p className="text-slate-500 text-xs">₹{info.negotiated_price} Total</p>
            </div>
          </div>

          {/* 3. The Coupon Code */}
          <div className="bg-white/5 p-4 rounded-xl border border-dashed border-white/20 text-center">
             <p className="text-[10px] text-slate-400 uppercase tracking-widest mb-2">Show this to driver</p>
             <div className="flex items-center justify-center gap-3">
               <QrCode size={40} className="text-white" />
               <div className="text-left">
                  <p className="text-xs text-slate-400">Secret Code</p>
                  <p className="text-2xl font-mono font-black text-yellow-400 tracking-wider">
                    {info.coupon_code}
                  </p>
               </div>
             </div>

             {/* WALLET ADDRESS DISPLAY */}
             {walletAddress && (
               <div className="mt-3 pt-3 border-t border-white/10 flex items-center justify-center gap-2 text-green-400/80">
                 <Wallet size={12} />
                 <p className="text-[10px] font-mono">
                   Owner: {walletAddress.slice(0,6)}...{walletAddress.slice(-4)}
                 </p>
               </div>
             )}
          </div>

          <button onClick={onClose} className="w-full py-4 bg-slate-800 rounded-xl font-bold text-slate-300 hover:bg-slate-700 transition">
            Close & Track Live
          </button>
        </div>
      </motion.div>
    </div>
  );
}