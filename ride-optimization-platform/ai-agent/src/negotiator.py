import random
import time
import json

class RideNegotiator:
    def __init__(self, ride_id, standard_price):
        self.ride_id = ride_id
        self.standard_price = standard_price
        self.current_bid = standard_price * 0.6  # Start low (60%)
        self.max_price = standard_price * 0.85   # Don't pay more than 85%

    def start_negotiation(self):
        """Simulates a conversation with Uber/Ola APIs"""
        history = []
        
        # Step 1: Initial Bid
        print(f"[AGENT] analyzing route {self.ride_id}...")
        time.sleep(1)
        history.append({"role": "agent", "message": f"Offering ₹{self.current_bid} for ride."})
        
        # Step 2: Driver Rejection (Simulated)
        time.sleep(1)
        driver_ask = self.standard_price * 0.95
        history.append({"role": "driver", "message": f"Too low. Market rate is ₹{self.standard_price}. I want ₹{driver_ask}."})
        
        # Step 3: Agent Counter-Bid
        time.sleep(1)
        self.current_bid = (self.current_bid + driver_ask) / 2
        history.append({"role": "agent", "message": f"Updated offer: ₹{int(self.current_bid)}. I have 3 passengers ready."})
        
        # Step 4: Agreement
        time.sleep(1)
        history.append({"role": "driver", "message": "Accepted. Sending vehicle details."})
        
        return {
            "status": "success",
            "final_price": int(self.current_bid),
            "logs": history
        }

if __name__ == "__main__":
    # Test run
    agent = RideNegotiator("RIDE-101", 800)
    result = agent.start_negotiation()
    print(json.dumps(result, indent=2))