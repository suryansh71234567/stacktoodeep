import React from 'react';
import { Navigation } from 'lucide-react';
import { motion } from 'framer-motion';

const MapDisplay = () => {
  // Animated Ghost Cars
  const ghostCars = [
    { id: 1, startX: '10%', startY: '20%', delay: 0 },
    { id: 2, startX: '80%', startY: '60%', delay: 2 },
    { id: 3, startX: '30%', startY: '80%', delay: 4 },
    { id: 4, startX: '60%', startY: '30%', delay: 1 },
    { id: 5, startX: '45%', startY: '10%', delay: 3 },
  ];

  return (
    <div className="w-full h-full min-h-[600px] bg-slate-950 rounded-3xl relative overflow-hidden group border border-slate-800 shadow-2xl">
      
      {/* 1. THE TECH GRID (Futuristic City Background) */}
      <div className="absolute inset-0 z-0 opacity-20"
           style={{
             backgroundImage: `
               linear-gradient(rgba(255, 255, 255, 0.1) 1px, transparent 1px),
               linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px)
             `,
             backgroundSize: '40px 40px'
           }}>
      </div>
      
      {/* 2. Radar Pulse Effect (The "Scanning" Animation) */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-blue-500/5 to-transparent z-0 animate-pulse-slow"></div>

      {/* 3. OPTIMIZED ROUTE VISUALIZATION (The "Daisy Chain" Logic) */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
        <defs>
          <linearGradient id="routeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0" />
            <stop offset="50%" stopColor="#fbbf24" stopOpacity="1" /> {/* Yellow Center */}
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
          </linearGradient>
        </defs>
        
        {/* The Route Path (Simulating A -> B -> C) */}
        <motion.path 
          d="M 100 400 Q 250 350 400 300 T 800 200" 
          fill="none"
          stroke="url(#routeGradient)"
          strokeWidth="4"
          strokeLinecap="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        />
        
        {/* Pulse Markers at Stops (Pooling Points) */}
        <circle cx="100" cy="400" r="4" fill="#3b82f6" className="animate-ping" />
        <circle cx="400" cy="300" r="4" fill="#fbbf24" className="animate-ping" style={{animationDelay: '1s'}} />
        <circle cx="800" cy="200" r="4" fill="#10b981" className="animate-ping" style={{animationDelay: '2s'}} />
      </svg>

      {/* 4. Ghost Cars (Yellow Dots simulating Traffic) */}
      {ghostCars.map((car) => (
        <motion.div
          key={car.id}
          initial={{ left: car.startX, top: car.startY, opacity: 0 }}
          animate={{ 
            left: [car.startX, `calc(${car.startX} + 150px)`, `calc(${car.startX} - 80px)`],
            top: [car.startY, `calc(${car.startY} + 80px)`, `calc(${car.startY} + 150px)`],
            opacity: [0, 1, 1, 0]
          }}
          transition={{ duration: 12, repeat: Infinity, delay: car.delay, ease: "linear" }}
          className="absolute z-10"
        >
          {/* Car Body */}
          <div className="w-3 h-3 bg-yellow-400 rounded-full shadow-[0_0_20px_rgba(250,204,21,0.8)] relative z-10"></div>
          {/* Headlights Beam */}
          <div className="absolute top-1/2 left-1/2 w-12 h-8 bg-gradient-to-r from-yellow-400/30 to-transparent -translate-y-1/2 rounded-full blur-md transform rotate-12"></div>
        </motion.div>
      ))}

      {/* 5. "You Are Here" Marker */}
      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-20">
        <div className="relative group cursor-pointer">
          <div className="absolute inset-0 bg-blue-500/40 rounded-full animate-ping"></div>
          <div className="relative bg-blue-600 text-white p-3 rounded-full border-4 border-slate-900 shadow-[0_0_30px_rgba(37,99,235,0.6)] transition-transform hover:scale-110">
            <Navigation size={28} fill="currentColor" />
          </div>
          {/* Tooltip */}
          <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-[10px] font-bold px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap border border-slate-600">
            Your Location
          </div>
        </div>
      </div>

      {/* 6. Live Stats Badge */}
      <div className="absolute bottom-8 right-8 bg-slate-900/90 backdrop-blur border border-slate-700 rounded-2xl p-4 shadow-xl z-20 flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
          <span className="text-xs font-bold text-slate-300">Live Traffic</span>
        </div>
        <div className="text-2xl font-black text-white">142 <span className="text-xs font-medium text-slate-500">drivers nearby</span></div>
      </div>
    </div>
  );
};

export default MapDisplay;