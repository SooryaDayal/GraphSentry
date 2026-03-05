import pandas as pd
import random
from datetime import datetime, timedelta
from pathlib import Path

class MuleDataGenerator:
    def __init__(self):
        self.channels = ['Mobile App', 'Web Banking', 'ATM', 'UPI', 'RTGS']
        self.normal_devices = [f"IMEI_{random.randint(10000, 99999)}" for _ in range(500)]
        self.normal_ips = [f"192.168.1.{random.randint(1, 255)}" for _ in range(200)]
        self.accounts = [f"ACT_{random.randint(1000, 9999)}" for _ in range(1000)]
        self.logs = []

    def generate_normal_traffic(self, num_records=1000):
        """Generates everyday, legitimate banking traffic (The 'Noise')."""
        start_time = datetime.now() - timedelta(days=7)
        
        for _ in range(num_records):
            random_minutes = random.randint(1, 10000)
            tx_time = start_time + timedelta(minutes=random_minutes)
            
            log = {
                'timestamp': tx_time.strftime('%Y-%m-%d %H:%M:%S'),
                'account_id': random.choice(self.accounts),
                'channel': random.choice(self.channels),
                'device_id': random.choice(self.normal_devices),
                'ip_address': random.choice(self.normal_ips),
                'transaction_type': 'Standard Transfer',
                'amount_inr': random.randint(100, 5000),
                'is_fraud_flag': 0
            }
            self.logs.append(log)

    def inject_mule_ring(self, ring_id, ring_size=10):
        """
        Simulates a 'Scam Hub' where one device/IP controls multiple accounts,
        executing 'Penny Drop' tests before a massive RTGS cash-out.
        """
        scam_device = f"IMEI_MULE_MASTER_{ring_id}"
        scam_ip = f"45.22.11.{ring_id}" 
        mule_accounts = [f"MULE_ACT_{ring_id}_{i}" for i in range(ring_size)]
        
        base_time = datetime.now() - timedelta(hours=24)

        for i, account in enumerate(mule_accounts):
            penny_drop_time = base_time + timedelta(minutes=(i * 5))
            cashout_time = penny_drop_time + timedelta(hours=2)

            # 1. The "Penny-Drop" Test Run (1 to 10 INR)
            self.logs.append({
                'timestamp': penny_drop_time.strftime('%Y-%m-%d %H:%M:%S'),
                'account_id': account,
                'channel': 'UPI',
                'device_id': scam_device,
                'ip_address': scam_ip,
                'transaction_type': 'Penny Drop Verification',
                'amount_inr': random.choice([1, 10]),
                'is_fraud_flag': 1
            })

            # 2. The Big RTGS Cash-Out
            self.logs.append({
                'timestamp': cashout_time.strftime('%Y-%m-%d %H:%M:%S'),
                'account_id': account,
                'channel': 'RTGS',
                'device_id': scam_device,
                'ip_address': scam_ip,
                'transaction_type': 'High-Value Transfer',
                'amount_inr': random.randint(50000, 200000),
                'is_fraud_flag': 1
            })

    def export_csv(self, filename="raw_bank_logs.csv"):
        """Saves the generated logs to a CSV file."""
        df = pd.DataFrame(self.logs)
        df = df.sort_values(by='timestamp').reset_index(drop=True)
        
        output_path = Path(__file__).parent / filename
        df.to_csv(output_path, index=False)
        print(f"[+] Generated {len(df)} total transactions.")
        print(f"[+] CSV successfully saved to: {output_path}")

# ==========================================
# EXECUTION BLOCK
# ==========================================
if __name__ == "__main__":
    print("[*] Initializing GraphSentry Data Generator...")
    gen = MuleDataGenerator()
    
    print("[*] Generating normal banking traffic...")
    gen.generate_normal_traffic(2000)
    
    print("[*] Injecting Mule Rings and Penny-Drop tests...")
    gen.inject_mule_ring(ring_id=99, ring_size=15)
    gen.inject_mule_ring(ring_id=88, ring_size=8)
    gen.inject_mule_ring(ring_id=77, ring_size=20)
    
    gen.export_csv()