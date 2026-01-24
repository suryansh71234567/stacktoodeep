import time
import random
import json
from colorama import Fore, Style, init
from bidding_strategy import BiddingEngine

# Initialize colors for terminal
init(autoreset=True)

class NegotiationSimulation:
    def __init__(self, route_name, standard_price):
        self.route_name = route_name
        self.engine = BiddingEngine(standard_price)
        self.current_offer = self.engine.get_initial_bid()
        self.is_deal_closed = False

    def simulated_driver_response(self, offer):
        """
        MOCK AI: Simulates a driver without needing an API Key.
        In production, replace this with LangChain call.
        """
        time.sleep(1.5) # Simulate thinking time
        
        threshold = self.engine.standard_price * 0.90
        
        if offer >= threshold:
            return {
                "message": "Okay bhai, chalo. Petrol is expensive but I will take it.",
                "accepted": True,
                "counter_offer": offer
            }
        else:
            # Driver counters with a higher price
            counter = max(offer + random.randint(30, 80), int(self.engine.standard_price * 0.85))
            rejections = [
                "Too low! Petrol is ₹100/liter.",
                "Are you joking? I can't go for that.",
                "Add some more, sir. Traffic is bad.",
                "This is peak hour. Give me better price."
            ]
            return {
                "message": random.choice(rejections),
                "accepted": False,
                "counter_offer": counter
            }

    def start(self):
        print(f"{Fore.CYAN}🚀 STARTING NEGOTIATION FOR: {self.route_name}")
        print(f"{Fore.CYAN}💰 Standard Market Rate: ₹{self.engine.standard_price}")
        print(f"{Fore.CYAN}🎯 Target Price: ₹{self.engine.max_price}")
        print("-" * 50)

        step = 1
        while not self.is_deal_closed and step <= 5:
            print(f"\n{Fore.YELLOW}[ROUND {step}]")
            
            # 1. Agent makes offer
            print(f"{Fore.GREEN}🤖 Nexus Agent: {Style.RESET_ALL}I can offer you ₹{self.current_offer}. We have 3 passengers ready.")

            # 2. Driver responds
            response = self.simulated_driver_response(self.current_offer)
            print(f"{Fore.RED}🚕 Driver Bot: {Style.RESET_ALL}{response['message']} (Asks ₹{response['counter_offer']})")

            # 3. Decision
            if response['accepted']:
                print(f"\n{Fore.GREEN}✅ DEAL SEALED at ₹{self.current_offer}!")
                self.is_deal_closed = True
                self.print_summary(self.current_offer)
            else:
                # Calculate next bid
                new_bid = self.engine.calculate_next_bid(response['counter_offer'])
                
                # Check if we walked away
                if new_bid == self.current_offer:
                    print(f"\n{Fore.RED}❌ NEGOTIATION FAILED. Driver wants too much.")
                    break
                    
                self.current_offer = new_bid
                step += 1

    def print_summary(self, final_price):
        stats = self.engine.evaluate_deal(final_price)
        print("-" * 50)
        print(f"{Fore.MAGENTA}🎉 SUCCESS TICKET GENERATED")
        print(f"Standard Price : ₹{stats['standard_rate']}")
        print(f"Negotiated Price: ₹{stats['final_rate']}")
        print(f"Total Savings   : ₹{stats['savings']} ({stats['discount_percent']}%)")
        print(f"Coupon Code     : NEX-{random.randint(1000,9999)}")
        print("-" * 50)

if __name__ == "__main__":
    # Test Run
    sim = NegotiationSimulation("Roorkee -> Dehradun", 800)
    sim.start()