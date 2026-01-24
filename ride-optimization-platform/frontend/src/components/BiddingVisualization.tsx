import React, { useEffect, useState, useRef } from 'react';
import { Bot, Car, CheckCircle2, Radio } from 'lucide-react';

export default function BiddingVisualization({ active }: { active: boolean }) {
  // 1. Defined the type explicitly to prevent TS confusion
  const [logs, setLogs] = useState<{icon: any, text: string, color: string}[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!active) {
      setLogs([]); // Clear logs when not active
      return;
    }

    const events = [
      { icon: Radio, text: "Broadcasting route to aggregator network...", color: "text-slate-400" },
      { icon: Bot, text: "AI Agent: Identified 8 pooling candidates", color: "text-blue-400" },
      { icon: Car, text: "Uber_XL bid received: ₹450", color: "text-orange-400" },
      { icon: Car, text: "Ola_Prime bid received: ₹435", color: "text-yellow-400" },
      { icon: Bot, text: "AI Agent: Negotiating bulk discount...", color: "text-purple-400" },
      { icon: Car, text: "Local_Fleet bid received: ₹390", color: "text-green-400" },
      { icon: CheckCircle2, text: "OPTIMAL MATCH FOUND: ₹390 (Saved ₹60)", color: "text-emerald-400 font-bold" }
    ];

    let i = 0;
    setLogs([]); // Reset immediately on start

    const interval = setInterval(() => {
      // 2. Added a safety check to ensure events[i] actually exists
      if (i < events.length && events[i]) {
        const newLog = events[i];
        setLogs(prev => [...prev, newLog]);
        i++;
        
        // Auto-scroll logic
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
      } else {
        clearInterval(interval);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [active]);

  return (
    <div className="glass-panel h-[450px] rounded-3xl p-6 flex flex-col relative overflow-hidden">
      {/* Header */}
      <div className="flex justify-between items-center mb-6 pb-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${active ? 'bg-green-500 animate-pulse' : 'bg-slate-600'}`}></div>
          <span className="font-mono text-xs tracking-widest text-slate-400 uppercase">Agent_Live_Feed</span>
        </div>
        <div className="px-2 py-1 bg-white/5 rounded text-[10px] font-mono text-slate-500 border border-white/5">
          NET_V1.0
        </div>
      </div>

      {/* Logs */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
        {!active && (
          <div className="h-full flex flex-col items-center justify-center opacity-20 space-y-3">
            <Radio size={40} />
            <p className="font-mono text-xs">WAITING FOR REQUEST...</p>
          </div>
        )}
        
        {logs.map((log, idx) => {
          // 3. CRITICAL FIX: Safety Guard. If log is undefined, skip rendering.
          if (!log) return null;

          return (
            <div key={idx} className="flex items-start gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className={`mt-0.5 ${log.color || 'text-white'}`}>
                <log.icon size={14} />
              </div>
              <span className={`font-mono text-xs leading-relaxed ${log.color?.includes('slate') ? 'text-slate-400' : 'text-slate-200'}`}>
                {log.text}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}