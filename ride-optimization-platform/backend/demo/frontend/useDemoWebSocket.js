/**
 * useDemoWebSocket - React Hook for Demo WebSocket
 * 
 * Copy to your React frontend: src/hooks/useDemoWebSocket.js
 * 
 * Usage:
 * ```jsx
 * import { useDemoWebSocket } from './hooks/useDemoWebSocket';
 * 
 * function DemoPage() {
 *   const { state, events, isConnected, startDemo, resetDemo } = useDemoWebSocket();
 *   
 *   return (
 *     <div>
 *       <p>Phase: {state.phase}</p>
 *       <button onClick={() => startDemo()}>Start Demo</button>
 *     </div>
 *   );
 * }
 * ```
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { initialDemoState } from './types';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const WS_URL = API_BASE.replace('http', 'ws') + '/demo/ws';

export function useDemoWebSocket() {
    const [state, setState] = useState(initialDemoState);
    const [events, setEvents] = useState([]);
    const [isConnected, setIsConnected] = useState(false);
    const wsRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);

    // Add event to the list
    const addEvent = useCallback((type, data) => {
        setEvents(prev => [...prev, { type, data, timestamp: new Date() }]);
    }, []);

    // Connect to WebSocket
    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        const ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            console.log('[Demo WS] Connected');
            setIsConnected(true);
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);

                // Add to event log
                if (message.type !== 'heartbeat' && message.type !== 'pong') {
                    addEvent(message.type, message.data);
                }

                // Update state based on event type
                switch (message.type) {
                    case 'CONNECTED':
                        setState(prev => ({ ...prev, ...message.data }));
                        break;

                    case 'PHASE_CHANGE':
                        setState(prev => ({
                            ...prev,
                            phase: message.data.phase,
                            bundle_id: message.data.bundle_id || prev.bundle_id
                        }));
                        break;

                    case 'AUCTION_CREATED':
                        setState(prev => ({
                            ...prev,
                            bundle_id: message.data.bundle_id,
                            bundle_hash: message.data.bundle_hash
                        }));
                        break;

                    case 'BID_COMMITTED':
                        setState(prev => ({
                            ...prev,
                            bids: [...prev.bids, {
                                company: message.data.company,
                                emoji: message.data.emoji,
                                color: message.data.color,
                                amount_eth: null,
                                is_revealed: false
                            }]
                        }));
                        break;

                    case 'BID_REVEALED':
                        setState(prev => ({
                            ...prev,
                            bids: prev.bids.map(bid =>
                                bid.company === message.data.company
                                    ? { ...bid, amount_eth: message.data.amount_eth, is_revealed: true }
                                    : bid
                            )
                        }));
                        break;

                    case 'WINNER_ANNOUNCED':
                        setState(prev => ({
                            ...prev,
                            winner: {
                                name: message.data.company,
                                emoji: message.data.emoji,
                                color: message.data.color,
                                address: message.data.address
                            },
                            winning_bid_eth: message.data.winning_bid_eth
                        }));
                        break;

                    case 'PAYMENT_RECORDED':
                        setState(prev => ({
                            ...prev,
                            payment_tx_hash: message.data.tx_hash
                        }));
                        break;

                    case 'DEMO_COMPLETE':
                        setState(prev => ({
                            ...prev,
                            phase: 'COMPLETED',
                            is_running: false
                        }));
                        break;

                    case 'ERROR':
                        setState(prev => ({
                            ...prev,
                            error: message.data.message
                        }));
                        break;

                    default:
                        break;
                }
            } catch (e) {
                console.error('[Demo WS] Parse error:', e);
            }
        };

        ws.onclose = () => {
            console.log('[Demo WS] Disconnected');
            setIsConnected(false);

            // Auto-reconnect after 3 seconds
            reconnectTimeoutRef.current = setTimeout(connect, 3000);
        };

        ws.onerror = (error) => {
            console.error('[Demo WS] Error:', error);
        };

        wsRef.current = ws;
    }, [addEvent]);

    // Start demo
    const startDemo = useCallback(async (speed = 1.0) => {
        setState(initialDemoState);
        setEvents([]);

        const response = await fetch(`${API_BASE}/demo/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ speed })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start demo');
        }

        setState(prev => ({ ...prev, is_running: true }));
    }, []);

    // Stop demo
    const stopDemo = useCallback(async () => {
        await fetch(`${API_BASE}/demo/stop`, { method: 'POST' });
        setState(prev => ({ ...prev, is_running: false }));
    }, []);

    // Reset demo
    const resetDemo = useCallback(async () => {
        await fetch(`${API_BASE}/demo/reset`, { method: 'POST' });
        setState(initialDemoState);
        setEvents([]);
    }, []);

    // Clear events
    const clearEvents = useCallback(() => {
        setEvents([]);
    }, []);

    // Connect on mount
    useEffect(() => {
        connect();

        return () => {
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
            wsRef.current?.close();
        };
    }, [connect]);

    return {
        state,
        events,
        isConnected,
        startDemo,
        stopDemo,
        resetDemo,
        clearEvents
    };
}

export default useDemoWebSocket;
