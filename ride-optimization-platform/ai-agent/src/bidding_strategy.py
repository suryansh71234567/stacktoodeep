class BiddingEngine:
    def __init__(self, standard_price):
        self.standard_price = standard_price
        self.min_price = standard_price * 0.70  # -30% (Start here)
        self.max_price = standard_price * 0.90  # -10% (Walk away here)
        self.current_round = 0

    def get_initial_bid(self):
        """Returns the starting lowball offer"""
        return int(self.min_price)

    def calculate_next_bid(self, driver_counter_offer):
        """Decides the next price based on game theory"""
        self.current_round += 1
        
        # If we are dragging on too long, jump to best price
        if self.current_round > 3:
            return int(self.max_price)

        # Split the difference strategy
        next_bid = (self.min_price + driver_counter_offer) / 2
        
        # Cap it at our max budget
        return int(min(next_bid, self.max_price))

    def evaluate_deal(self, final_agreed_price):
        """Calculates how much money we saved"""
        savings = self.standard_price - final_agreed_price
        return {
            "standard_rate": self.standard_price,
            "final_rate": final_agreed_price,
            "savings": savings,
            "discount_percent": round((savings / self.standard_price) * 100, 1)
        }