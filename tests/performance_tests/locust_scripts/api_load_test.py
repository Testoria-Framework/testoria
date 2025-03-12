import time
import json
import random
import string
import os
from locust import HttpUser, task, between, tag

class ApiUser(HttpUser):
    """
    Simulates a user interacting with the API
    """
    # Wait between 1 and 5 seconds between tasks
    wait_time = between(1, 5)
    
    # Store IDs for later use
    user_id = None
    product_id = None
    order_id = None
    
    def on_start(self):
        """
        Initialize the user session
        """
        # Set default headers
        self.client.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _random_string(self, length=8, chars=string.ascii_lowercase + string.digits):
        """Generate a random string"""
        return ''.join(random.choice(chars) for _ in range(length))
    
    def _random_phone(self):
        """Generate a random phone number"""
        return f"+1{random.randint(2, 9)}{random.randint(0, 9)}{''.join(str(random.randint(0, 9)) for _ in range(8))}"
    
    def _generate_user_data(self):
        """Generate random user data"""
        return {
            "name": f"Test User {self._random_string(5)}",
            "email": f"test.{self._random_string(8)}@example.com",
            "phone": self._random_phone()
        }
    
    def _generate_product_data(self):
        """Generate random product data"""
        return {
            "name": f"Test Product {self._random_string(5)}",
            "description": "A test product created via performance tests",
            "price": round(random.uniform(10, 200), 2),
            "category": "test",
            "stock": random.randint(50, 500),
            "sku": f"TEST-{self._random_string(6, string.ascii_uppercase + string.digits)}"
        }
    
    def _generate_order_data(self):
        """Generate random order data"""
        return {
            "customer_id": random.randint(100, 999),
            "items": [
                {
                    "product_id": random.randint(1, 10),
                    "quantity": random.randint(1, 5),
                    "price": round(random.uniform(10, 100), 2)
                },
                {
                    "product_id": random.randint(11, 20),
                    "quantity": random.randint(1, 3),
                    "price": round(random.uniform(20, 200), 2)
                }
            ],
            "shipping_address": {
                "street": f"{random.randint(100, 999)} Main St",
                "city": "Test City",
                "state": "TS",
                "zip": ''.join(random.choice(string.digits) for _ in range(5)),
                "country": "Test Country"
            }
        }
    
    @tag('users')
    @task(3)
    def get_all_users(self):
        """Get all users"""
        with self.client.get("/users", name="GET All Users") as response:
            if response.status_code == 200:
                users = response.json()
                if users and len(users) > 0:
                    # Store a user ID for later use
                    self.user_id = users[0]["id"]
    
    @tag('users')
    @task(4)
    def get_user_by_id(self):
        """Get a specific user by ID"""
        # Use the stored user ID or default to 1
        user_id = self.user_id or 1
        self.client.get(f"/users/{user_id}", name="GET User by ID")
    
    @tag('users')
    @task(2)
    def create_user(self):
        """Create a new user"""
        user_data = self._generate_user_data()
        with self.client.post("/users", json=user_data, name="POST Create User") as response:
            if response.status_code == 201:
                created_user = response.json()
                self.user_id = created_user["id"]
    
    @tag('products')
    @task(3)
    def get_all_products(self):
        """Get all products"""
        with self.client.get("/products", name="GET All Products") as response:
            if response.status_code == 200:
                products = response.json()
                if products and len(products) > 0:
                    # Store a product ID for later use
                    self.product_id = products[0]["id"]
    
    @tag('products')
    @task(4)
    def get_product_by_id(self):
        """Get a specific product by ID"""
        # Use the stored product ID or default to P001
        product_id = self.product_id or "P001"
        self.client.get(f"/products/{product_id}", name="GET Product by ID")
    
    @tag('products')
    @task(2)
    def get_products_by_category(self):
        """Get products by category"""
        self.client.get("/products?category=electronics", name="GET Products by Category")
    
    @tag('products')
    @task(2)
    def create_product(self):
        """Create a new product"""
        product_data = self._generate_product_data()
        with self.client.post("/products", json=product_data, name="POST Create Product") as response:
            if response.status_code == 201:
                created_product = response.json()
                self.product_id = created_product["id"]
    
    @tag('orders')
    @task(3)
    def get_all_orders(self):
        """Get all orders"""
        with self.client.get("/orders", name="GET All Orders") as response:
            if response.status_code == 200:
                orders = response.json()
                if orders and len(orders) > 0:
                    # Store an order ID for later use
                    self.order_id = orders[0]["id"]
    
    @tag('orders')
    @task(4)
    def get_order_by_id(self):
        """Get a specific order by ID"""
        # Use the stored order ID or default to ORD-001
        order_id = self.order_id or "ORD-001"
        self.client.get(f"/orders/{order_id}", name="GET Order by ID")
    
    @tag('orders')
    @task(2)
    def create_order(self):
        """Create a new order"""
        order_data = self._generate_order_data()
        with self.client.post("/orders", json=order_data, name="POST Create Order") as response:
            if response.status_code == 201:
                created_order = response.json()
                self.order_id = created_order["id"]
    
    @tag('orders')
    @task(1)
    def update_order_status(self):
        """Update an order status"""
        # Use the stored order ID or default to ORD-001
        order_id = self.order_id or "ORD-001"
        update_data = {
            "status": "shipped",
            "tracking_number": f"TRACK{self._random_string(8, string.digits)}"
        }
        self.client.patch(f"/orders/{order_id}", json=update_data, name="PATCH Update Order")

if __name__ == "__main__":
    # This is for running standalone, Locust will use its own command-line parsing when run from CLI
    from locust.env import Environment
    from locust.stats import stats_printer, stats_history
    from locust.log import setup_logging
    import gevent
    
    # Set up logging
    setup_logging("INFO", None)
    
    # Create an environment
    env = Environment(user_classes=[ApiUser])
    env.create_local_runner()
    
    # Start the test
    env.runner.start(50, spawn_rate=10)
    
    # Print stats in the console
    gevent.spawn(stats_printer(env.stats))
    
    # Save stats to history
    gevent.spawn(stats_history, env.runner)
    
    # Run for 60 seconds
    time.sleep(60)
    
    # Stop the test
    env.runner.quit()
