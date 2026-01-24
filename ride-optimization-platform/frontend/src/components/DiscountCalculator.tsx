import React from 'react';
import { Wallet, TrendingDown, Zap } from 'lucide-react';
import { motion } from 'framer-motion';

const DiscountCalculator: React.FC<{ patience: number }> = ({ patience }) => {
  const savings = (patience * 2.5).toFixed(0);
  const percent = Math.min((patience * 1.2), 40).toFixed(0);

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass-panel p-6 rounded-2xl border-t-2 border-t-green-500/50 mt-6 relative overflow-hidden"
    >
      {/* Background Glow */}
      <div className="absolute top-0 right-0 w-24 h-24 bg-green-500/10 blur-2xl rounded-full -mr-10 -mt-10"></div>

      <div className="flex justify-between items-start relative z-10">
        <div>
          <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Projected Savings</p>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-bold text-white">₹{savings}</span>
            <span className="text-sm text-slate-400 font-medium">/ ride</span>
          </div>
        </div>
        
        <div className="bg-green-500/10 p-2.5 rounded-xl text-green-400">
          <Wallet size={24} />
        </div>
      </div>

      <div className="mt-4 flex items-center gap-3">
        <div className="bg-green-500/10 px-3 py-1.5 rounded-lg flex items-center gap-1.5 border border-green-500/20">
          <TrendingDown size={14} className="text-green-400" />
          <span className="text-xs font-bold text-green-400">{percent}% Cheaper</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <Zap size={12} className="text-yellow-400" />
          <span>vs Standard Uber</span>
        </div>
      </div>
    </motion.div>
  );
};

export default DiscountCalculator;