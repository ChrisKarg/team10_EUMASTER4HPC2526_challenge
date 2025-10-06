# run_inference.py
import torch
import time

# Simple linear model
model = torch.nn.Linear(1000, 1000)
data = torch.randn(1000, 1000)

start = time.time()
for _ in range(100):
    out = model(data)
end = time.time()

print(f"Inference finished in {end - start:.4f} seconds")
