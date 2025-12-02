#!/usr/bin/env python3
"""
Run Evaluation Pipeline
Generates synthetic data and runs a load test to measure system performance.
"""

import sys
import os
import argparse
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.matching.evaluation.pipeline import EvaluationPipeline
from core.db.engine import engine
from sqlmodel import Session

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def main():
    parser = argparse.ArgumentParser(description="Run Performance Evaluation")
    parser.add_argument("--count", type=int, default=50, help="Number of CVs to process")
    parser.add_argument("--jobs", type=int, default=20, help="Number of Jobs to generate")
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrency level")
    parser.add_argument("--synthetic", action="store_true", default=True, help="Use synthetic data")
    
    args = parser.parse_args()
    
    print(f"🚀 Starting Evaluation Pipeline")
    print(f"Configuration: {args.count} CVs, {args.jobs} Jobs, Concurrency: {args.concurrency}")
    print("-" * 50)
    
    # Initialize pipeline
    # We pass a session to log metrics to the DB
    with Session(engine) as session:
        pipeline = EvaluationPipeline(db_session=session)
        
        # 1. Generate Data
        data = pipeline.generate_synthetic_data(num_cvs=args.count, num_jobs=args.jobs)
        cvs = data["cvs"]
        
        # 2. Run Load Test
        print("\nRunning Load Test...")
        results = pipeline.run_load_test(cvs, concurrency=args.concurrency)
        
        # 3. Report
        print("\n📊 Performance Report")
        print("=" * 50)
        print(f"Total Processed:    {results['total_processed']}")
        print(f"Success Rate:       {results['success_count']}/{results['total_processed']}")
        print(f"Total Time:         {results['total_time_seconds']}s")
        print(f"Throughput:         {results['throughput_rpm']} CVs/min")
        print(f"Average Latency:    {results['avg_latency_seconds'] * 1000:.2f} ms")
        print(f"P95 Latency:        {results['p95_latency'] * 1000:.2f} ms")
        print(f"P99 Latency:        {results['p99_latency'] * 1000:.2f} ms")
        print("=" * 50)
        
        # 4. Check DB for logged metrics
        print("\nVerifying DB Metrics...")
        metrics = pipeline.monitor.get_system_metrics()
        print(f"DB Reported Avg Latency: {metrics.get('avg_latency_ms')} ms")
        print(f"DB Reported Throughput:  {metrics.get('throughput_rpm')} rpm")

if __name__ == "__main__":
    main()
