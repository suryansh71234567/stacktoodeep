import React, { useState } from 'react';
import { Clock, ArrowRight, Loader2, Navigation, Car, Users, Briefcase } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Props {
  onOptimize: () => void;
  patience: number;
  setPatience: (val: number) => void;
}

interface LocationResult { display_name: string; lat: string; lon: string; }

const CAR_TYPES = [
  { id: 'mini', name: 'Mini', icon: Car, desc: 'Hatchback', price: '1x' },
  { id: 'sedan', name: 'Sedan', icon: Briefcase, desc: 'Sedan', price: '1.2x' },
  { id: 'suv', name: 'SUV', icon: Users, desc: 'SUV/MUV', price: '1.5x' },
];

const RideRequestForm: React.FC<Props> = ({ onOptimize, patience, setPatience }) => {
  const [pickupQuery, setPickupQuery] = useState('');
  const [dropQuery, setDropQuery] = useState('');
  const [pickupSuggestions, setPickupSuggestions] = useState<LocationResult[]>([]);
  const [dropSuggestions, setDropSuggestions] = useState<LocationResult[]>([]);
  const [pickupValid, setPickupValid] = useState(false);
  const [dropValid, setDropValid] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedCar, setSelectedCar] = useState('mini');

  const searchLocation = async (query: string, type: 'pickup' | 'drop') => {
    if (query.length < 3) return;
    setLoading(true);
    try {
      const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}&limit=5`);
      const data = await res.json();
      type === 'pickup' ? setPickupSuggestions(data) : setDropSuggestions(data);
    } catch (err) { console.error(err); } 
    finally { setLoading(false); }
  };

  const selectLocation = (loc: LocationResult, type: 'pickup' | 'drop') => {
    if (type === 'pickup') {
      setPickupQuery(loc.display_name.split(',')[0]);
      setPickupSuggestions([]);
      setPickupValid(true);
    } else {
      setDropQuery(loc.display_name.split(',')[0]);
      setDropSuggestions([]);
      setDropValid(true);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      className="glass-panel p-8 rounded-[2rem] w-full relative z-20 border-t-4 border-t-yellow-400 shadow-2xl"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <h2 className="text-2xl font-bold text-white tracking-tight">Book Your Ride</h2>
        <span className="bg-yellow-400/20 text-yellow-400 text-xs font-bold px-3 py-1.5 rounded-lg border border-yellow-400/20">
          BEST PRICE GUARANTEE
        </span>
      </div>

      <div className="space-y-6 relative">
        
        {/* PICKUP */}
        <div className="relative z-50 group">
          <label className="text-xs font-bold text-slate-300 uppercase ml-1 mb-2 block tracking-wider">Pickup Location</label>
          <div className="relative">
            <div className={`absolute left-4 top-4 w-3 h-3 rounded-full ${pickupValid ? 'bg-green-500' : 'bg-yellow-500'}`}></div>
            {/* Increased padding (p-4) and Font Size (text-lg) */}
            <input 
              type="text" value={pickupQuery}
              onChange={(e) => { setPickupQuery(e.target.value); setPickupValid(false); searchLocation(e.target.value, 'pickup'); }}
              placeholder="Enter City, Airport, or Hotel" 
              className="glass-input w-full pl-10 p-4 rounded-xl text-lg font-medium placeholder:text-slate-500"
            />
            {loading && <Loader2 className="absolute right-4 top-4 animate-spin text-slate-400" size={20} />}
          </div>
          
          <AnimatePresence>
            {pickupSuggestions.length > 0 && (
              <motion.ul initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="absolute w-full bg-slate-900 border border-slate-700 rounded-xl shadow-2xl mt-2 overflow-hidden z-50">
                {pickupSuggestions.map((loc, idx) => (
                  <li key={idx} onClick={() => selectLocation(loc, 'pickup')} className="p-4 hover:bg-slate-800 cursor-pointer text-sm text-slate-200 border-b border-slate-800 flex items-center gap-3">
                    <Navigation size={16} className="text-slate-500" /> {loc.display_name}
                  </li>
                ))}
              </motion.ul>
            )}
          </AnimatePresence>
        </div>

        {/* DROPOFF */}
        <div className="relative z-40 group">
          <label className="text-xs font-bold text-slate-300 uppercase ml-1 mb-2 block tracking-wider">Dropoff Location</label>
          <div className="relative">
            <div className={`absolute left-4 top-4 w-3 h-3 rounded-full ${dropValid ? 'bg-red-500' : 'bg-slate-500'}`}></div>
            <input 
              type="text" value={dropQuery}
              onChange={(e) => { setDropQuery(e.target.value); setDropValid(false); searchLocation(e.target.value, 'drop'); }}
              placeholder="Enter Destination" 
              className="glass-input w-full pl-10 p-4 rounded-xl text-lg font-medium placeholder:text-slate-500"
            />
          </div>
          <AnimatePresence>
            {dropSuggestions.length > 0 && (
              <motion.ul initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="absolute w-full bg-slate-900 border border-slate-700 rounded-xl shadow-2xl mt-2 overflow-hidden z-50">
                {dropSuggestions.map((loc, idx) => (
                  <li key={idx} onClick={() => selectLocation(loc, 'drop')} className="p-4 hover:bg-slate-800 cursor-pointer text-sm text-slate-200 border-b border-slate-800 flex items-center gap-3">
                    <Navigation size={16} className="text-slate-500" /> {loc.display_name}
                  </li>
                ))}
              </motion.ul>
            )}
          </AnimatePresence>
        </div>

        {/* CAR SELECTION - Bigger Cards */}
        <div className="pt-2">
          <label className="text-xs font-bold text-slate-300 uppercase ml-1 mb-3 block tracking-wider">Select Vehicle</label>
          <div className="grid grid-cols-3 gap-3">
            {CAR_TYPES.map((car) => (
              <div 
                key={car.id}
                onClick={() => setSelectedCar(car.id)}
                className={`p-4 rounded-2xl border cursor-pointer transition-all flex flex-col items-center text-center
                  ${selectedCar === car.id 
                    ? 'bg-yellow-500 text-black border-yellow-500 shadow-xl shadow-yellow-500/20 scale-105' 
                    : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:bg-slate-800 hover:border-slate-600'}`}
              >
                <car.icon size={28} className="mb-2" />
                <span className="text-sm font-bold">{car.name}</span>
                <span className={`text-xs ${selectedCar === car.id ? 'text-black/80 font-semibold' : 'text-slate-500'}`}>{car.desc}</span>
              </div>
            ))}
          </div>
        </div>

        {/* PATIENCE SLIDER - Bigger Touch Area */}
        <div className="pt-6 border-t border-white/10 relative z-10">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-2">
              <Clock size={20} className="text-yellow-400" />
              <span className="text-base font-bold text-white">Flexibility Savings</span>
            </div>
            <span className="text-yellow-400 font-bold bg-yellow-400/10 px-4 py-1.5 rounded-lg text-sm border border-yellow-400/20">
              {patience} min wait
            </span>
          </div>
          <input 
            type="range" min="0" max="60" step="5" value={patience}
            onChange={(e) => setPatience(Number(e.target.value))}
            className="w-full accent-yellow-400 cursor-pointer h-2 rounded-lg bg-slate-700 appearance-none"
          />
        </div>

        {/* ACTION BUTTON - Massive */}
        <button 
          onClick={onOptimize}
          disabled={!pickupValid || !dropValid}
          className={`w-full py-5 rounded-2xl font-bold text-black shadow-lg flex items-center justify-center gap-3 mt-4 transition-all text-base uppercase tracking-wider
            ${pickupValid && dropValid 
              ? 'bg-yellow-400 hover:bg-yellow-300 hover:shadow-yellow-400/40 hover:scale-[1.02] cursor-pointer' 
              : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
            }`}
        >
          {pickupValid && dropValid ? 'Search Optimized Cabs' : 'Select Locations First'} <ArrowRight size={20} />
        </button>
      </div>
    </motion.div>
  );
};

export default RideRequestForm;