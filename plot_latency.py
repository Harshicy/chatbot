import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta

# Simulated data based on project context
start_time = datetime(2025, 4, 15, 0, 0)
times = [start_time + timedelta(hours=i) for i in range(24)]
latencies = [
    2.5, 2.7, 2.9, 3.0, 2.8, 2.6, 2.4, 2.2,  # Initial high latency (00:00-07:00)
    2.0, 1.9, 1.8, 1.7, 1.6, 1.5, 1.6, 1.7,  # Optimization effect (08:00-15:00)
    1.8, 2.0, 2.1, 2.3, 2.5, 2.8, 3.0, 2.6   # Spike and stabilization (16:00-23:00)
]  # ms converted to seconds for readability

# Create DataFrame
df = pd.DataFrame({'timestamp': times, 'latency_ms': [l * 1000 for l in latencies]})  # Convert to ms

# Plot
plt.figure(figsize=(12, 6))
plt.plot(df['timestamp'], df['latency_ms'], label='Latency (ms)', color='blue', marker='o')
plt.xlabel('Time (2025-04-15)')
plt.ylabel('Latency (ms)')
plt.title('Latency of Basic Chatbot on Render Deployment')
plt.legend()
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('latency_chart.png')
plt.show()