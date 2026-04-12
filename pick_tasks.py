"""Randomly pick N task names from the Terminal-Bench 2.0 dataset (89 tasks)."""
import os, random, sys

tasks_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks_2.0.txt")
with open(tasks_file) as f:
    all_tasks = [line.strip() for line in f if line.strip()]

n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
picked = random.sample(all_tasks, min(n, len(all_tasks)))

print(" ".join(picked))
