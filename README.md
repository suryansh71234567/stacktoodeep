# 🚖 Bharat Moves (Nexus Agent)

> **India's First AI-Agentic Ride Optimization Platform.** > *Trade your time for money. We negotiate bulk deals with Uber, Ola, and local fleets in real-time.*

![Project Banner](https://img.shields.io/badge/Status-Hackathon%20MVP-orange?style=for-the-badge) 
![Tech Stack](https://img.shields.io/badge/Tech-Next.js%20%7C%20Tailwind%20%7C%20Python-blue?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

---

##  The Problem
In the current mobility market, price is king. However, **Time Flexibility** is an undervalued asset.
* **Users** pay high surge prices even when they aren't in a rush.
* **Drivers** return empty-handed on return trips (dead-heading).
* **Aggregators** struggle to optimize pooled rides efficiently.

##  The Solution: Reverse Auction Mobility
**Bharat Moves** is a brokerage layer that sits between travelers and major cab providers.
1.  **User Sets Flexibility:** "I can leave between 5:00 PM and 5:30 PM."
2.  **Route Optimization:** Our engine groups flexible users into high-value route bundles.
3.  **AI Bidding Agents:** An autonomous AI Agent negotiates this bundle with Uber, Ola, and local fleets.
4.  **Profit Sharing:** The savings generated from efficient routing are shared with the user as a **Discount Coupon**.

---

##  Key Features (Frontend Implemented)

###  Rapido-Style Immersive Map
* **Full-Screen Dark Mode Map** powered by Mapbox aesthetics.
* **Live Ghost Traffic:** Animated cars moving in real-time to simulate network density.
* **Route Visualization:** Glowing pathfinding lines showing the optimized trip.

###  The Flexibility Slider (USP)
* Users input their **Time Buffer** (e.g., 15 min wait).
* **Real-time Feedback:** As you slide, the estimated savings increase instantly.

###  Live Agent Bidding Visualization
* A transparent "Matrix-style" terminal showing the backend logic.
* Watch as the AI rejects high bids from Uber and accepts low bids from local drivers.

###  Smart Coupon Generation
* Upon successful negotiation, users receive a **QR Code Ticket**.
* This ensures the discount is locked and verifiable.

---

##  Tech Stack

### **Frontend (Completed)**
* **Framework:** Next.js 14 (React)
* **Styling:** Tailwind CSS (Glassmorphism & Neobrutalism)
* **Animations:** Framer Motion (Smooth transitions & map effects)
* **Icons:** Lucide React
* **Maps:** CSS Grid Pattern + SVG Overlays (No API Key required for demo)

### **Backend (Roadmap)**
* **Server:** Python FastAPI
* **Optimization:** Google OR-Tools (VRP Solver)
* **AI Agents:** LangChain + OpenAI API (Negotiation Logic)


##  Getting Started

Follow these steps to set up the project locally.

### Prerequisites
* Node.js (v18 or higher)
* npm or yarn

### Installation

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/suryansh71234567/stacktoodeep.git](https://github.com/suryansh71234567/stacktoodeep.git)
    cd stacktoodeep/ride-optimization-platform/frontend
    ```

2.  **Install Dependencies**
    ```bash
    npm install
    ```

3.  **Run the Development Server**
    ```bash
    npm run dev
    ```

4.  **Open in Browser**
    Visit `http://localhost:3000` to see the app in action.

---

##  Roadmap

- [x] **Phase 1: Frontend MVP** (High-fidelity UI, Animations, Mock Data)
- [ ] **Phase 2: Backend Integration** (FastAPI connection, Real geocoding)
- [ ] **Phase 3: AI Agent Core** (LangChain integration for real bidding)
- [ ] **Phase 4: Blockchain Escrow** (Smart contract for secure coupon redemption)

---

##  Contributing

We welcome contributions! Please follow these steps:
1.  Fork the repository.
2.  Create your feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

---

* **Lakshya Gupta** - Frontend Engineering & UX

---

*Built with ❤️ for the Hackathon 2026*
