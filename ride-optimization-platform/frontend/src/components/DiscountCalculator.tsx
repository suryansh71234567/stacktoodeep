import React from 'react';
import { TrendingDown, Clock, Banknote, Car } from 'lucide-react';

interface DiscountProps {
  patience: number;
  distance: number;
}

export default function DiscountCalculator({ patience, distance }: DiscountProps) {
  
  // REALISTIC PRICING CONSTANTS
  const FUEL_COST = 18; // ₹18 per km (Fuel + Maintenance)
  const DRIVER_BASE_FARE = 50; // Base pickup fee
  
  // Formula: (Distance * 2 for Round Trip * Fuel) + Base
  const standardPrice = (distance * 2 * FUEL_COST) + DRIVER_BASE_FARE;

  // Max discount 40% based on patience
  const discountPercent = Math.min(patience * 1.5, 40); 
  const discountAmount = Math.floor((standardPrice * discountPercent) / 100);
  const finalPrice = Math.floor(standardPrice - discountAmount);

  return (
    <div className="bg-slate-900/50 p-6 rounded-2xl border border-white/10 backdrop-blur-sm transition-all duration-300">
      <h3 className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-4 flex items-center gap-2">
        <Banknote size={14} /> Live Price Estimation
      </h3>

      {/* VISUAL DISTANCE CHECK */}
      <div className="flex justify-between items-center mb-4 p-2 bg-slate-800/50 rounded-lg border border-white/5">
        <div className="flex items-center gap-2 text-slate-300">
           <Car size={14} className="text-yellow-400"/>
           <span className="text-xs font-medium">Trip Distance</span>
        </div>
        <span className="text-sm font-mono font-bold text-white">{distance} km</span>
      </div>

      <div className="space-y-4">
        {/* Row 1: The Standard Market Price */}
        <div className="flex justify-between items-center opacity-60">
          <span className="text-sm font-medium text-slate-400">Standard Rate</span>
          <span className="text-sm font-mono text-slate-300 line-through decoration-red-500/50">
            ₹{standardPrice}
          </span>
        </div>

        {/* Row 2: Your Savings */}
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2 text-green-400">
            <TrendingDown size={16} />
            <span className="text-sm font-bold">Buffer Savings ({Math.floor(discountPercent)}%)</span>
          </div>
          <span className="text-sm font-mono font-bold text-green-400">
            - ₹{discountAmount}
          </span>
        </div>

        <div className="h-px w-full bg-white/10 my-2"></div>

        {/* Row 3: Final Price */}
        <div className="flex justify-between items-end">
          <div>
            <span className="text-xs text-slate-500 font-medium block mb-1">YOU PAY ONLY</span>
            <div className="flex items-center gap-2 text-[10px] text-yellow-400/80 bg-yellow-400/10 px-2 py-0.5 rounded border border-yellow-400/20">
               <Clock size={10} />
               <span>Waiting {patience} mins</span>
            </div>
          </div>
          <div className="text-right">
            <span className="text-4xl font-black text-white tracking-tighter">
              ₹{finalPrice}
            </span>
          </div>
        </div>
      </div>
      
      <div className="mt-3 text-[9px] text-slate-600 text-center">
        *Includes Round Trip & Base Fare
      </div>
    </div>
  );
}