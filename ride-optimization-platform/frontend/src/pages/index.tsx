import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import RideRequestForm from '../components/RideRequestForm';
import DiscountCalculator from '../components/DiscountCalculator';
import BiddingVisualization from '../components/BiddingVisualization';
import MapDisplay from '../components/MapDisplay';
import SuccessTicket from '../components/SuccessTicket';
import { ShieldCheck, Zap, Globe } from 'lucide-react';

export default function Home() {
  const [patience, setPatience] = useState(15);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [showTicket, setShowTicket] = useState(false);

  // THE "GAME LOOP" LOGIC
  useEffect(() => {
    if (isOptimizing) {
      // 1. User clicked "Find Driver". Start the Bidding Animation.
      // 2. Wait 8 seconds (Simulating API negotiation)
      const timer = setTimeout(() => {
        setIsOptimizing(false); // Stop Bidding
        setShowTicket(true);    // Show the Coupon!
      }, 8000);

      return () => clearTimeout(timer);
    }
  }, [isOptimizing]);

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-50 overflow-hidden relative selection:bg-yellow-400 selection:text-black flex flex-col">
      <Head>
        <title>Bharat Moves | Advanced Ride Optimization</title>
      </Head>

      {/* 0. SUCCESS MODAL (Overlays everything when active) */}
      {showTicket && <SuccessTicket onClose={() => setShowTicket(false)} />}

      {/* 1. NAVBAR (Fixed Top) */}
      <nav className="w-full h-20 border-b border-white/5 bg-slate-900/80 backdrop-blur-md flex-none z-50">
        <div className="w-full h-full px-8 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 bg-yellow-400 rounded-xl flex items-center justify-center shadow-lg shadow-yellow-400/20">
              <Zap className="text-black fill-black" size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tighter text-white leading-none">BHARAT<span className="text-yellow-400">MOVES</span></h1>
            </div>
          </div>
          <div className="flex items-center gap-6 text-sm font-bold text-slate-300">
            <span className="hidden md:block hover:text-yellow-400 cursor-pointer transition">Drive</span>
            <span className="hidden md:block hover:text-yellow-400 cursor-pointer transition">Enterprise</span>
            <button className="bg-white text-black px-6 py-2.5 rounded-full font-bold hover:bg-yellow-400 transition shadow-lg">
              Sign In
            </button>
          </div>
        </div>
      </nav>

      {/* 2. MAIN SPLIT CONTENT */}
      <div className="flex-1 flex flex-row overflow-hidden relative">
        
        {/* LEFT PANEL (Input Section) */}
        <div className="w-full lg:w-[600px] h-full overflow-y-auto custom-scrollbar bg-slate-950 relative z-30 flex flex-col px-8 py-8 lg:px-12 gap-6 shadow-[10px_0_50px_rgba(0,0,0,0.5)]">
          
          {/* Header Section */}
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-yellow-400/10 border border-yellow-400/20 text-yellow-400 text-[10px] font-bold mb-4 tracking-wider uppercase">
              <Globe size={12} /> Live Across India
            </div>
            <h1 className="text-5xl lg:text-6xl font-black text-white leading-[0.95] mb-4 tracking-tight">
              Move Freely.<br/>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-orange-500">
                Save massive.
              </span>
            </h1>
            <p className="text-slate-400 text-base font-medium leading-relaxed max-w-md">
              Nexus Agent negotiates bulk deals with Uber, Ola, and local fleets in real-time.
            </p>
          </div>

          {/* The Booking Form */}
          <RideRequestForm 
            onOptimize={() => setIsOptimizing(true)} 
            patience={patience} 
            setPatience={setPatience} 
          />

          {/* Savings Calculator */}
          <DiscountCalculator patience={patience} />
          
          {/* Trust Footers */}
          <div className="mt-auto pt-8 border-t border-white/5 flex items-center gap-6 opacity-60 grayscale hover:grayscale-0 transition-all duration-500">
             <div className="flex items-center gap-2">
              <ShieldCheck className="text-green-400" size={16} />
              <span className="text-xs font-bold text-slate-300">Verified Drivers</span>
            </div>
            <div className="flex items-center gap-2">
              <Zap className="text-yellow-400" size={16} />
              <span className="text-xs font-bold text-slate-300">Instant Booking</span>
            </div>
          </div>
        </div>

        {/* RIGHT PANEL (Map & Agent Overlay) */}
        <div className="hidden lg:block flex-1 h-full relative bg-slate-900">
          
          {/* Agent Bidding Overlay (Only appears when optimizing) */}
          {isOptimizing && (
            <div className="absolute top-8 left-8 z-50 w-96 animate-in fade-in zoom-in duration-300 drop-shadow-2xl">
              <BiddingVisualization active={true} />
            </div>
          )}

          {/* Map Component */}
          <div className="w-full h-full relative">
             {/* Gradient Fade to blend map with sidebar */}
             <div className="absolute inset-y-0 left-0 w-32 bg-gradient-to-r from-slate-950 to-transparent z-20 pointer-events-none"></div>
             <MapDisplay />
          </div>
        </div>

      </div>
    </div>
  );
}