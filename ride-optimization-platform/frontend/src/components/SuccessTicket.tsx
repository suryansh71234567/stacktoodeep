import React from 'react';
import { motion } from 'framer-motion';
import { QrCode, Copy, CheckCircle, Car, Star } from 'lucide-react';

export default function SuccessTicket({ onClose }: { onClose: () => void }) {
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
          <p className="text-black/80 font-bold text-sm">You saved ₹142 on this ride</p>
        </div>

        {/* 2. Ticket Details */}
        <div className="p-6 space-y-6 relative">
          {/* Jagged Line Effect */}
          <div className="absolute top-0 left-0 w-full h-4 -mt-2 bg-slate-900" style={{clipPath: "polygon(0 0, 5% 100%, 10% 0, 15% 100%, 20% 0, 25% 100%, 30% 0, 35% 100%, 40% 0, 45% 100%, 50% 0, 55% 100%, 60% 0, 65% 100%, 70% 0, 75% 100%, 80% 0, 85% 100%, 90% 0, 95% 100%, 100% 0)"}}></div>

          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div>
              <p className="text-xs text-slate-400 uppercase font-bold">Driver</p>
              <p className="text-lg font-bold text-white">Rajesh Kumar</p>
              <div className="flex items-center gap-1 text-yellow-400 text-xs">
                <Star size={10} fill="currentColor" /> 4.8 Rating
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-400 uppercase font-bold">Vehicle</p>
              <p className="text-white font-medium">Swift Dzire</p>
              <p className="text-slate-500 text-xs">UK-07-AB-1234</p>
            </div>
          </div>

          {/* 3. The Coupon Code */}
          <div className="bg-white/5 p-4 rounded-xl border border-dashed border-white/20 text-center">
             <p className="text-[10px] text-slate-400 uppercase tracking-widest mb-2">Show this to driver</p>
             <div className="flex items-center justify-center gap-3">
               <QrCode size={40} className="text-white" />
               <div className="text-left">
                  <p className="text-xs text-slate-400">Secret Code</p>
                  <p className="text-2xl font-mono font-black text-yellow-400 tracking-wider">NEX-8821</p>
               </div>
             </div>
          </div>

          <button onClick={onClose} className="w-full py-4 bg-slate-800 rounded-xl font-bold text-slate-300 hover:bg-slate-700 transition">
            Close & Track Live
          </button>
        </div>
      </motion.div>
    </div>
  );
}