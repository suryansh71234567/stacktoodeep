import React from 'react';
import { TrendingDown, Clock, Banknote, Car, Timer } from 'lucide-react';

interface DiscountProps {
  patience: number;      // Buffer time in minutes
  distance: number;      // Trip distance in km
  preferredTime: string; // ISO string of preferred departure time
}

export default function DiscountCalculator({ patience, distance, preferredTime }: DiscountProps) {

  // =========================================================================
  // PRICING CONSTANTS
  // =========================================================================
  const FUEL_COST = 18;           // ₹18 per km (Fuel + Maintenance)
  const DRIVER_BASE_FARE = 50;    // Base pickup fee
  const K_FACTOR = 2;             // Maximum discount cap = K * distance (₹ per km)

  // Discount rates
  const ADVANCE_BOOKING_RATE = 0.5;  // 0.5% per hour of advance booking
  const MAX_ADVANCE_HOURS = 24;       // Cap at 24 hours advance
  const BUFFER_RATE = 0.67;           // ~40% max for 60 min buffer (0.67% per minute)
  const MAX_BUFFER_DISCOUNT = 40;     // Maximum buffer discount percentage

  // =========================================================================
  // CALCULATIONS
  // =========================================================================

  // Standard price (without any discounts)
  const standardPrice = (distance * 2 * FUEL_COST) + DRIVER_BASE_FARE;

  // 1. ADVANCE BOOKING DISCOUNT
  // Calculate hours until departure
  const now = new Date();
  const departure = new Date(preferredTime);
  const hoursUntilDeparture = Math.max(0, (departure.getTime() - now.getTime()) / (1000 * 60 * 60));
  const cappedHours = Math.min(hoursUntilDeparture, MAX_ADVANCE_HOURS);

  // Advance discount: 0.5% per hour, max 12% (for 24 hours)
  const advanceDiscountPercent = cappedHours * ADVANCE_BOOKING_RATE;

  // 2. BUFFER TIME DISCOUNT
  // Buffer discount: increases with patience, max 40%
  const bufferDiscountPercent = Math.min(patience * BUFFER_RATE, MAX_BUFFER_DISCOUNT);

  // 3. TOTAL DISCOUNT (uncapped)
  const totalDiscountPercent = advanceDiscountPercent + bufferDiscountPercent;

  // 4. MAXIMUM DISCOUNT CAP = K * distance
  const maxDiscountAmount = K_FACTOR * distance;
  const maxDiscountPercent = (maxDiscountAmount / standardPrice) * 100;

  // 5. FINAL DISCOUNT (capped)
  const finalDiscountPercent = Math.min(totalDiscountPercent, maxDiscountPercent, 50); // Also cap at 50%
  const discountAmount = Math.floor((standardPrice * finalDiscountPercent) / 100);
  const finalPrice = Math.floor(standardPrice - discountAmount);

  return (
    <div className="bg-slate-900/50 p-6 rounded-2xl border border-white/10 backdrop-blur-sm transition-all duration-300">
      <h3 className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-4 flex items-center gap-2">
        <Banknote size={14} /> Live Price Estimation
      </h3>

      {/* VISUAL DISTANCE CHECK */}
      <div className="flex justify-between items-center mb-4 p-2 bg-slate-800/50 rounded-lg border border-white/5">
        <div className="flex items-center gap-2 text-slate-300">
          <Car size={14} className="text-yellow-400" />
          <span className="text-xs font-medium">Trip Distance</span>
        </div>
        <span className="text-sm font-mono font-bold text-white">{distance} km</span>
      </div>

      <div className="space-y-3">
        {/* Row 1: The Standard Market Price */}
        <div className="flex justify-between items-center opacity-60">
          <span className="text-sm font-medium text-slate-400">Standard Rate</span>
          <span className="text-sm font-mono text-slate-300 line-through decoration-red-500/50">
            ₹{standardPrice}
          </span>
        </div>

        {/* Row 2: Advance Booking Discount */}
        {advanceDiscountPercent > 0 && (
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2 text-blue-400">
              <Timer size={14} />
              <span className="text-xs font-medium">
                Advance Booking ({Math.floor(cappedHours)}h ahead: {advanceDiscountPercent.toFixed(1)}%)
              </span>
            </div>
            <span className="text-xs font-mono font-bold text-blue-400">
              - ₹{Math.floor((standardPrice * advanceDiscountPercent) / 100)}
            </span>
          </div>
        )}

        {/* Row 3: Buffer Time Discount */}
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2 text-green-400">
            <TrendingDown size={16} />
            <span className="text-sm font-bold">Buffer Savings ({bufferDiscountPercent.toFixed(1)}%)</span>
          </div>
          <span className="text-sm font-mono font-bold text-green-400">
            - ₹{Math.floor((standardPrice * bufferDiscountPercent) / 100)}
          </span>
        </div>

        {/* Discount Cap Notice (if applicable) */}
        {totalDiscountPercent > finalDiscountPercent && (
          <div className="text-[10px] text-orange-400/70 text-center py-1 bg-orange-400/10 rounded border border-orange-400/20">
            Discount capped at ₹{discountAmount} (max {finalDiscountPercent.toFixed(0)}% for {distance}km trip)
          </div>
        )}

        <div className="h-px w-full bg-white/10 my-2"></div>

        {/* Row 4: Final Price */}
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
            <span className="block text-xs text-green-400 font-bold">
              Total: {finalDiscountPercent.toFixed(0)}% off
            </span>
          </div>
        </div>
      </div>

      <div className="mt-3 text-[9px] text-slate-600 text-center">
        *Advance ({advanceDiscountPercent.toFixed(1)}%) + Buffer ({bufferDiscountPercent.toFixed(1)}%) = {totalDiscountPercent.toFixed(1)}% → Capped at {finalDiscountPercent.toFixed(0)}%
      </div>
    </div>
  );
}