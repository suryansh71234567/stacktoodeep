import React, { useState, useEffect } from 'react';
import { Calendar, Clock, MapPin, Navigation, Search } from 'lucide-react';
import { searchLocations, calculateHaversineDistance, LocationData } from '../utils/distance';

interface FormProps {
  onOptimize: () => void;
  patience: number;
  setPatience: (val: number) => void;
  setTripDistance: (km: number) => void;
  setPickupCoords: (coords: { lat: number, lon: number } | null) => void;
  setDropCoords: (coords: { lat: number, lon: number } | null) => void;
  setPreferredTime: (time: string) => void;
}

export default function RideRequestForm({ onOptimize, patience, setPatience, setTripDistance, setPickupCoords: setParentPickupCoords, setDropCoords: setParentDropCoords, setPreferredTime }: FormProps) {
  // 1. Initialize with Valid Coords (Roorkee -> Dehradun)
  // This ensures the initial price is REAL, not hardcoded 55km.
  const [pickupCoords, setPickupCoords] = useState<{ lat: number, lon: number } | null>({ lat: 29.8543, lon: 77.8880 });
  const [dropCoords, setDropCoords] = useState<{ lat: number, lon: number } | null>({ lat: 30.3165, lon: 78.0322 });

  const [pickupQuery, setPickupQuery] = useState("IIT Roorkee");
  const [dropQuery, setDropQuery] = useState("Clock Tower, Dehradun");

  const [pickupSuggestions, setPickupSuggestions] = useState<LocationData[]>([]);
  const [dropSuggestions, setDropSuggestions] = useState<LocationData[]>([]);

  // Time State
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [time, setTime] = useState("10:00");

  // --- LIVE SEARCH HANDLER ---
  const handleSearch = async (query: string, type: 'pickup' | 'drop') => {
    if (type === 'pickup') setPickupQuery(query);
    else setDropQuery(query);

    if (query.length > 2) {
      const results = await searchLocations(query);
      if (type === 'pickup') setPickupSuggestions(results);
      else setDropSuggestions(results);
    } else {
      if (type === 'pickup') setPickupSuggestions([]);
      else setDropSuggestions([]);
    }
  };

  // --- SELECTION HANDLER (Crucial Step) ---
  const selectLocation = (loc: LocationData, type: 'pickup' | 'drop') => {
    // 1. Parse coordinates
    const coords = { lat: parseFloat(loc.lat), lon: parseFloat(loc.lon) };

    // 2. Update State
    if (type === 'pickup') {
      setPickupQuery(loc.display_name.split(',')[0]);
      setPickupCoords(coords);
      setPickupSuggestions([]);
    } else {
      setDropQuery(loc.display_name.split(',')[0]);
      setDropCoords(coords);
      setDropSuggestions([]);
    }
  };

  // --- CALCULATE DISTANCE AUTOMATICALLY ---
  useEffect(() => {
    if (pickupCoords && dropCoords) {
      const dist = calculateHaversineDistance(
        pickupCoords.lat, pickupCoords.lon,
        dropCoords.lat, dropCoords.lon
      );
      console.log(`New Distance Calculated: ${dist} km`); // Debug log
      setTripDistance(dist);
    }
  }, [pickupCoords, dropCoords, setTripDistance]);

  // --- SYNC COORDINATES TO PARENT ---
  useEffect(() => {
    setParentPickupCoords(pickupCoords);
  }, [pickupCoords, setParentPickupCoords]);

  useEffect(() => {
    setParentDropCoords(dropCoords);
  }, [dropCoords, setParentDropCoords]);

  // --- SYNC PREFERRED TIME TO PARENT ---
  useEffect(() => {
    const preferredDateTime = `${date}T${time}:00`;
    setPreferredTime(preferredDateTime);
  }, [date, time, setPreferredTime]);

  return (
    <div className="space-y-6">

      {/* 1. LOCATION SEARCH INPUTS */}
      <div className="space-y-4 relative">

        {/* PICKUP INPUT */}
        <div className="relative group z-30">
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">
            <MapPin size={18} />
          </div>
          <input
            type="text"
            value={pickupQuery}
            onChange={(e) => handleSearch(e.target.value, 'pickup')}
            className="w-full bg-slate-900 border border-white/10 rounded-xl py-4 pl-12 pr-4 text-white font-medium focus:outline-none focus:border-yellow-400/50 transition-all placeholder:text-slate-600"
            placeholder="Search Pickup (Click list to select!)"
          />

          {/* Pickup Suggestions */}
          {pickupSuggestions.length > 0 && (
            <div className="absolute top-full left-0 w-full bg-slate-800 border border-white/10 rounded-xl mt-1 shadow-2xl overflow-hidden max-h-60 overflow-y-auto z-40">
              {pickupSuggestions.map((loc, i) => (
                <div
                  key={i}
                  onClick={() => selectLocation(loc, 'pickup')}
                  className="p-3 hover:bg-white/10 cursor-pointer border-b border-white/5 last:border-0 text-sm text-slate-300 truncate"
                >
                  {loc.display_name}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* DROP INPUT */}
        <div className="relative group z-20">
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">
            <Navigation size={18} />
          </div>
          <input
            type="text"
            value={dropQuery}
            onChange={(e) => handleSearch(e.target.value, 'drop')}
            className="w-full bg-slate-900 border border-white/10 rounded-xl py-4 pl-12 pr-4 text-white font-medium focus:outline-none focus:border-yellow-400/50 transition-all placeholder:text-slate-600"
            placeholder="Search Drop (Click list to select!)"
          />

          {/* Drop Suggestions */}
          {dropSuggestions.length > 0 && (
            <div className="absolute top-full left-0 w-full bg-slate-800 border border-white/10 rounded-xl mt-1 shadow-2xl overflow-hidden max-h-60 overflow-y-auto z-40">
              {dropSuggestions.map((loc, i) => (
                <div
                  key={i}
                  onClick={() => selectLocation(loc, 'drop')}
                  className="p-3 hover:bg-white/10 cursor-pointer border-b border-white/5 last:border-0 text-sm text-slate-300 truncate"
                >
                  {loc.display_name}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 2. DATE & TIME (Standard Inputs) */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-slate-900 border border-white/10 rounded-xl p-2 flex items-center gap-3">
          <div className="p-2 bg-white/5 rounded-lg text-slate-400"><Calendar size={18} /></div>
          <div className="flex-1">
            <p className="text-[10px] text-slate-500 font-bold uppercase">Date</p>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="w-full bg-transparent text-white text-sm font-bold focus:outline-none [color-scheme:dark]" />
          </div>
        </div>

        <div className="bg-slate-900 border border-white/10 rounded-xl p-2 flex items-center gap-3">
          <div className="p-2 bg-white/5 rounded-lg text-slate-400"><Clock size={18} /></div>
          <div className="flex-1">
            <p className="text-[10px] text-slate-500 font-bold uppercase">Time</p>
            <input type="time" value={time} onChange={(e) => setTime(e.target.value)} className="w-full bg-transparent text-white text-sm font-bold focus:outline-none [color-scheme:dark]" />
          </div>
        </div>
      </div>

      {/* 3. SLIDER */}
      <div className="bg-yellow-400/5 border border-yellow-400/20 rounded-2xl p-5">
        <div className="flex justify-between items-center mb-4">
          <label className="text-yellow-400 font-bold text-sm flex items-center gap-2">
            <Clock size={16} /> Buffer Time
          </label>
          <span className="bg-yellow-400 text-black text-xs font-bold px-2 py-1 rounded">
            {patience} min wait
          </span>
        </div>
        <input
          type="range" min="0" max="60" value={patience}
          onChange={(e) => setPatience(Number(e.target.value))}
          className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-yellow-400"
        />
        <div className="flex justify-between mt-2 text-[10px] text-slate-500 font-medium">
          <span>Urgent (0m)</span>
          <span>Max Savings (60m)</span>
        </div>
      </div>

      <button onClick={onOptimize} className="w-full bg-yellow-400 hover:bg-yellow-300 text-black font-black py-4 rounded-xl text-lg uppercase tracking-wide transition-all shadow-lg">
        Search Optimized Cabs
      </button>

    </div>
  );
}