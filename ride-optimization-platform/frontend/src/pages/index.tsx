import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import RideRequestForm from '../components/RideRequestForm';
import DiscountCalculator from '../components/DiscountCalculator';
import BiddingVisualization from '../components/BiddingVisualization';
import MapDisplay from '../components/MapDisplay';
import SuccessTicket from '../components/SuccessTicket';
import ConnectWallet from '../components/ConnectWallet';
import { ShieldCheck, Zap, Globe } from 'lucide-react';

export default function Home() {
  const [patience, setPatience] = useState(15);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [showTicket, setShowTicket] = useState(false);

  // NEW STATE: Trip Distance (Shared between Form and Calculator)
  const [tripDistance, setTripDistance] = useState(55);

  const [userWallet, setUserWallet] = useState("");
  const [apiResult, setApiResult] = useState(null);

  // --- THE REAL BACKEND INTEGRATION ---
  useEffect(() => {
    if (isOptimizing) {


      // Construct Payload - Matching Backend Pydantic Model (RideRequest)
      const requestPayload = {
        ride_requests: [
          {
            user_id: "demo_user_001",
            location_start: {
              lat: 29.8543,
              lng: 77.8880 // Roorkee
            },
            location_end: {
              lat: 30.3165,
              lng: 78.0322 // Dehradun
            },
            ride_time: new Date(new Date().getTime() + 60 * 60 * 1000).toISOString(), // 1 hour from now
            buffer_after_min: patience, // Maps to 'patience'
            buffer_before_min: 15 // Default flexibility
          }
        ]
      };

      const API_URL = 'http://127.0.0.1:8000/optimize';

      fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestPayload)
      })
        .then(res => res.json())
        .then(data => {
          console.log("Optimization Result:", data);
          setApiResult(data);

          // Wait 5 seconds for the "Matrix Animation"
          setTimeout(() => {
            setIsOptimizing(false);
            setShowTicket(true);
          }, 5000);
        })
        .catch(err => {
          console.error("Backend Connection Error:", err);
          setIsOptimizing(false);
        });
    }
  }, [isOptimizing, patience]);

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-50 overflow-hidden relative selection:bg-yellow-400 selection:text-black flex flex-col">
      <Head>
        <title>Bharat Moves | Advanced Ride Optimization</title>
      </Head>

      {/* 0. SUCCESS MODAL */}
      {showTicket && (
        <SuccessTicket
          onClose={() => setShowTicket(false)}
          data={apiResult}
          walletAddress={userWallet}
        />
      )}

      {/* 1. NAVBAR */}
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
            {/* CONNECT WALLET BUTTON */}
            <ConnectWallet onConnect={setUserWallet} />
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
              Move Freely.<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-orange-500">
                Save massive.
              </span>
            </h1>
            <p className="text-slate-400 text-base font-medium leading-relaxed max-w-md">
              Nexus Agent negotiates bulk deals with Uber, Ola, and local fleets in real-time.
            </p>
          </div>

          {/* THE BOOKING FORM (Now passes distance setter) */}
          <RideRequestForm
            onOptimize={() => setIsOptimizing(true)}
            patience={patience}
            setPatience={setPatience}
            setTripDistance={setTripDistance} // <--- Added Prop
          />

          {/* SAVINGS CALCULATOR (Now receives dynamic distance) */}
          <DiscountCalculator
            patience={patience}
            distance={tripDistance} // <--- Added Prop
          />

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

          {/* Agent Bidding Overlay */}
          {isOptimizing && (
            <div className="absolute top-8 left-8 z-50 w-96 animate-in fade-in zoom-in duration-300 drop-shadow-2xl">
              <BiddingVisualization active={true} />
            </div>
          )}

          {/* Map Component */}
          <div className="w-full h-full relative">
            <div className="absolute inset-y-0 left-0 w-32 bg-gradient-to-r from-slate-950 to-transparent z-20 pointer-events-none"></div>
            <MapDisplay />
          </div>
        </div>

      </div>
    </div>
  );
}