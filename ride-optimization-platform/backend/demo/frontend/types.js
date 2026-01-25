/**
 * Demo Types - For use with Demo WebSocket
 * 
 * Copy to your React frontend: src/hooks/types.js
 * For TypeScript: rename to types.ts
 */

// Demo phases
export const DEMO_PHASES = {
    IDLE: 'IDLE',
    CREATING: 'CREATING',
    COMMIT: 'COMMIT',
    REVEAL: 'REVEAL',
    FINALIZING: 'FINALIZING',
    PAYMENT: 'PAYMENT',
    COMPLETED: 'COMPLETED'
};

// Initial state for demo
export const initialDemoState = {
    phase: 'IDLE',
    bundle_id: '',
    bundle_hash: null,
    bids: [],
    winner: null,
    winning_bid_eth: 0,
    payment_tx_hash: '',
    error: null,
    is_running: false
};
