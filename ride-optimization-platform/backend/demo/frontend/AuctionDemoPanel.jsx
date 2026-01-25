/**
 * AuctionDemoPanel - React Component for Hackathon Demo
 * 
 * Copy to your React frontend: src/components/AuctionDemoPanel.jsx
 * 
 * Usage:
 * ```jsx
 * import AuctionDemoPanel from './components/AuctionDemoPanel';
 * 
 * function App() {
 *   return <AuctionDemoPanel />;
 * }
 * ```
 */

import React, { useState } from 'react';
import { useDemoWebSocket } from '../hooks/useDemoWebSocket';
import { DEMO_PHASES } from '../hooks/types';

// Phase configuration
const PHASES = [
    { key: 'IDLE', label: 'Ready', icon: '⏸️' },
    { key: 'CREATING', label: 'Creating', icon: '📝' },
    { key: 'COMMIT', label: 'Bidding', icon: '🔒' },
    { key: 'REVEAL', label: 'Reveal', icon: '👁️' },
    { key: 'FINALIZING', label: 'Finalizing', icon: '⚖️' },
    { key: 'PAYMENT', label: 'Payment', icon: '💳' },
    { key: 'COMPLETED', label: 'Done', icon: '✅' },
];

// Styles
const styles = {
    container: {
        maxWidth: '1200px',
        margin: '0 auto',
        padding: '24px',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        backgroundColor: '#0a0a0f',
        minHeight: '100vh',
        color: '#fff',
    },
    header: {
        textAlign: 'center',
        marginBottom: '32px',
    },
    title: {
        fontSize: '32px',
        fontWeight: 'bold',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        marginBottom: '8px',
    },
    subtitle: {
        color: '#888',
        fontSize: '14px',
    },
    connectionBadge: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '4px 12px',
        borderRadius: '16px',
        fontSize: '12px',
        marginTop: '8px',
    },
    grid: {
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '24px',
    },
    card: {
        backgroundColor: '#1a1a2e',
        borderRadius: '16px',
        padding: '24px',
        border: '1px solid #2a2a4a',
    },
    cardTitle: {
        fontSize: '18px',
        fontWeight: '600',
        marginBottom: '16px',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
    },
    phaseTimeline: {
        display: 'flex',
        justifyContent: 'space-between',
        marginBottom: '24px',
        position: 'relative',
    },
    phaseStep: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        flex: 1,
        position: 'relative',
        zIndex: 1,
    },
    phaseDot: {
        width: '40px',
        height: '40px',
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '16px',
        marginBottom: '8px',
        transition: 'all 0.3s ease',
    },
    phaseLabel: {
        fontSize: '12px',
        color: '#888',
    },
    bidCard: {
        backgroundColor: '#0f0f1a',
        borderRadius: '12px',
        padding: '16px',
        marginBottom: '12px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        animation: 'slideIn 0.3s ease',
    },
    bidEmoji: {
        fontSize: '32px',
    },
    bidInfo: {
        flex: 1,
    },
    bidCompany: {
        fontWeight: '600',
        marginBottom: '4px',
    },
    bidAmount: {
        fontSize: '14px',
        color: '#888',
    },
    winnerCard: {
        backgroundColor: '#1a2f1a',
        border: '2px solid #4ade80',
        borderRadius: '16px',
        padding: '24px',
        textAlign: 'center',
        animation: 'pulse 2s infinite',
    },
    winnerEmoji: {
        fontSize: '64px',
        marginBottom: '16px',
    },
    winnerName: {
        fontSize: '24px',
        fontWeight: 'bold',
        marginBottom: '8px',
    },
    winnerBid: {
        fontSize: '32px',
        color: '#4ade80',
        fontWeight: 'bold',
    },
    paymentFlow: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '16px',
        padding: '24px',
    },
    paymentNode: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '8px',
    },
    paymentArrow: {
        fontSize: '24px',
        color: '#4ade80',
        animation: 'moveRight 1s infinite',
    },
    eventLog: {
        backgroundColor: '#0f0f1a',
        borderRadius: '8px',
        padding: '12px',
        maxHeight: '200px',
        overflowY: 'auto',
        fontSize: '12px',
        fontFamily: 'monospace',
    },
    eventItem: {
        padding: '4px 0',
        borderBottom: '1px solid #2a2a4a',
        display: 'flex',
        gap: '8px',
    },
    buttonPrimary: {
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: '#fff',
        border: 'none',
        padding: '12px 32px',
        borderRadius: '8px',
        fontSize: '16px',
        fontWeight: '600',
        cursor: 'pointer',
        transition: 'transform 0.2s, box-shadow 0.2s',
    },
    buttonSecondary: {
        backgroundColor: '#2a2a4a',
        color: '#fff',
        border: 'none',
        padding: '12px 24px',
        borderRadius: '8px',
        fontSize: '14px',
        cursor: 'pointer',
    },
    controls: {
        display: 'flex',
        justifyContent: 'center',
        gap: '16px',
        marginTop: '24px',
    },
};

// Bid Card Component
function BidCard({ bid, index }) {
    return (
        <div
            style={{
                ...styles.bidCard,
                borderLeft: `4px solid ${bid.color}`,
                animationDelay: `${index * 0.1}s`
            }}
        >
            <div style={styles.bidEmoji}>{bid.emoji}</div>
            <div style={styles.bidInfo}>
                <div style={styles.bidCompany}>{bid.company}</div>
                <div style={styles.bidAmount}>
                    {bid.is_revealed
                        ? `${bid.amount_eth?.toFixed(3)} ETH`
                        : '🔒 Sealed Bid'
                    }
                </div>
            </div>
            {bid.is_revealed && (
                <div style={{ color: '#4ade80', fontSize: '20px' }}>✓</div>
            )}
        </div>
    );
}

// Phase Timeline Component
function PhaseTimeline({ currentPhase }) {
    const currentIndex = PHASES.findIndex(p => p.key === currentPhase);

    return (
        <div style={styles.phaseTimeline}>
            {/* Progress bar background */}
            <div style={{
                position: 'absolute',
                top: '20px',
                left: '10%',
                right: '10%',
                height: '4px',
                backgroundColor: '#2a2a4a',
                borderRadius: '2px',
                zIndex: 0,
            }} />

            {/* Progress bar fill */}
            <div style={{
                position: 'absolute',
                top: '20px',
                left: '10%',
                width: `${Math.max(0, (currentIndex / (PHASES.length - 1)) * 80)}%`,
                height: '4px',
                background: 'linear-gradient(90deg, #667eea, #764ba2)',
                borderRadius: '2px',
                zIndex: 0,
                transition: 'width 0.5s ease',
            }} />

            {PHASES.map((phase, index) => {
                const isActive = index === currentIndex;
                const isPast = index < currentIndex;

                return (
                    <div key={phase.key} style={styles.phaseStep}>
                        <div style={{
                            ...styles.phaseDot,
                            backgroundColor: isActive ? '#667eea' : isPast ? '#4ade80' : '#2a2a4a',
                            boxShadow: isActive ? '0 0 20px rgba(102, 126, 234, 0.5)' : 'none',
                            transform: isActive ? 'scale(1.2)' : 'scale(1)',
                        }}>
                            {phase.icon}
                        </div>
                        <div style={{
                            ...styles.phaseLabel,
                            color: isActive ? '#fff' : isPast ? '#4ade80' : '#888',
                            fontWeight: isActive ? '600' : '400',
                        }}>
                            {phase.label}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

// Main Component
export function AuctionDemoPanel() {
    const { state, events, isConnected, startDemo, stopDemo, resetDemo } = useDemoWebSocket();
    const [isStarting, setIsStarting] = useState(false);

    const handleStart = async () => {
        setIsStarting(true);
        try {
            await startDemo(1.0);
        } catch (e) {
            console.error(e);
        } finally {
            setIsStarting(false);
        }
    };

    const handleReset = async () => {
        await resetDemo();
    };

    return (
        <div style={styles.container}>
            {/* Header */}
            <header style={styles.header}>
                <h1 style={styles.title}>🔗 Blockchain Auction Demo</h1>
                <p style={styles.subtitle}>
                    Real-time sealed-bid auction with AI Agent x402 payment
                </p>
                <div style={{
                    ...styles.connectionBadge,
                    backgroundColor: isConnected ? '#1a2f1a' : '#2f1a1a',
                    color: isConnected ? '#4ade80' : '#f87171',
                }}>
                    <span style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        backgroundColor: isConnected ? '#4ade80' : '#f87171',
                    }} />
                    {isConnected ? 'Connected' : 'Disconnected'}
                </div>
            </header>

            {/* Phase Timeline */}
            <PhaseTimeline currentPhase={state.phase} />

            {/* Main Grid */}
            <div style={styles.grid}>
                {/* Left Column - Bids */}
                <div style={styles.card}>
                    <h3 style={styles.cardTitle}>
                        <span>🏢</span> Company Bids
                    </h3>

                    {state.bids.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: '40px', color: '#888' }}>
                            Waiting for auction to start...
                        </div>
                    ) : (
                        state.bids.map((bid, index) => (
                            <BidCard key={bid.company} bid={bid} index={index} />
                        ))
                    )}
                </div>

                {/* Right Column - Winner & Payment */}
                <div>
                    {/* Winner Card */}
                    {state.winner && (
                        <div style={{ ...styles.card, ...styles.winnerCard, marginBottom: '24px' }}>
                            <div style={styles.winnerEmoji}>{state.winner.emoji}</div>
                            <div style={styles.winnerName}>🏆 {state.winner.name}</div>
                            <div style={styles.winnerBid}>{state.winning_bid_eth.toFixed(3)} ETH</div>
                        </div>
                    )}

                    {/* Payment Flow */}
                    {(state.phase === 'PAYMENT' || state.phase === 'COMPLETED') && (
                        <div style={styles.card}>
                            <h3 style={styles.cardTitle}>
                                <span>🤖</span> AI Agent Payment Flow
                            </h3>
                            <div style={styles.paymentFlow}>
                                <div style={styles.paymentNode}>
                                    <div style={{ fontSize: '40px' }}>🤖</div>
                                    <div>AI Agent</div>
                                </div>
                                <div style={styles.paymentArrow}>→ 💰 →</div>
                                <div style={styles.paymentNode}>
                                    <div style={{ fontSize: '40px' }}>{state.winner?.emoji || '🏢'}</div>
                                    <div>{state.winner?.name || 'Winner'}</div>
                                </div>
                            </div>
                            {state.payment_tx_hash && (
                                <div style={{
                                    textAlign: 'center',
                                    marginTop: '16px',
                                    padding: '12px',
                                    backgroundColor: '#0f0f1a',
                                    borderRadius: '8px',
                                    fontSize: '12px',
                                    fontFamily: 'monospace'
                                }}>
                                    <div style={{ color: '#888', marginBottom: '4px' }}>Transaction Hash:</div>
                                    <div style={{ color: '#4ade80' }}>{state.payment_tx_hash}</div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Event Log */}
                    <div style={{ ...styles.card, marginTop: '24px' }}>
                        <h3 style={styles.cardTitle}>
                            <span>📋</span> Event Log
                        </h3>
                        <div style={styles.eventLog}>
                            {events.slice(-10).reverse().map((event, i) => (
                                <div key={i} style={styles.eventItem}>
                                    <span style={{ color: '#888' }}>
                                        {event.timestamp.toLocaleTimeString()}
                                    </span>
                                    <span style={{ color: '#667eea' }}>{event.type}</span>
                                </div>
                            ))}
                            {events.length === 0 && (
                                <div style={{ color: '#888', textAlign: 'center' }}>
                                    No events yet
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Controls */}
            <div style={styles.controls}>
                <button
                    style={{
                        ...styles.buttonPrimary,
                        opacity: state.is_running || isStarting ? 0.5 : 1,
                        cursor: state.is_running || isStarting ? 'not-allowed' : 'pointer',
                    }}
                    onClick={handleStart}
                    disabled={state.is_running || isStarting}
                >
                    {isStarting ? '⏳ Starting...' : '🚀 Start Demo'}
                </button>

                <button
                    style={styles.buttonSecondary}
                    onClick={handleReset}
                >
                    🔄 Reset
                </button>
            </div>

            {/* Error Display */}
            {state.error && (
                <div style={{
                    marginTop: '24px',
                    padding: '16px',
                    backgroundColor: '#2f1a1a',
                    border: '1px solid #f87171',
                    borderRadius: '8px',
                    color: '#f87171',
                    textAlign: 'center',
                }}>
                    ⚠️ {state.error}
                </div>
            )}

            {/* Keyframes CSS */}
            <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(-20px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes pulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.4); }
          50% { box-shadow: 0 0 20px 10px rgba(74, 222, 128, 0); }
        }
        @keyframes moveRight {
          0%, 100% { transform: translateX(0); }
          50% { transform: translateX(5px); }
        }
      `}</style>
        </div>
    );
}

export default AuctionDemoPanel;
