#!/usr/bin/env python3
"""
Full Resume Evaluation & Visualization Script - REVISED VERSION

- Computes pairwise resume similarity using FullResumeEvaluator
- Generates section-wise and overall metrics
- Visualizes all metrics in one combined figure with improved layout and metrics.
    1. Overall Similarity Heatmap (with annotations)
    2. Section Performance Bar Chart (Corrected P/R/F1 display)
    3. Average Section F1 Radar Chart
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import matplotlib.pyplot as plt
import logging

# --- Setup for mock environment ---
# This is a placeholder for your actual imports/classes
class MockResumeEvaluator:
    """Mock class to simulate the actual evaluator's methods and results structure."""
    def evaluate_resume(self, gt_A: Dict, pred_B: Dict) -> Dict:
        # Simulate Section F1, Precision (P), Recall (R)
        # Using a fixed pattern for demonstration purposes
        A_id = gt_A.get('meta', {}).get('id', 'A').split('_')[0]
        B_id = pred_B.get('meta', {}).get('id', 'B').split('_')[0]
        base = 1.0 if A_id == B_id else (0.8 if A_id[0] == B_id[0] else 0.2)

        results = {}
        sections = ["basics", "work", "education", "skills", "awards", "languages", "interests"]
        np.random.seed(hash(A_id + B_id) % 2**32) # Seed for reproducibility in the mock

        for sec in sections:
            # Simulate slight variance for non-identical comparison
            f1_base = base * (1.0 - np.random.rand() * 0.1)
            # F1 = (2 * P * R) / (P + R). For non-identical, let P and R diverge slightly
            
            # For demonstration, ensure P, R, and F1 are distinct when not 1.0
            if A_id == B_id:
                p, r, f1 = 1.0, 1.0, 1.0
            else:
                # Mock Precision and Recall such that they are close to f1_base
                # For example: P > R means high Precision but low Recall
                if np.random.rand() < 0.5: # Simulate P > R (High quality, missing some content)
                    p = min(1.0, f1_base + np.random.rand() * 0.1)
                    r = max(0.0, f1_base - np.random.rand() * 0.1)
                else: # Simulate R > P (High content capture, low quality/noise)
                    r = min(1.0, f1_base + np.random.rand() * 0.1)
                    p = max(0.0, f1_base - np.random.rand() * 0.1)

                # Recalculate F1 from the mocked P and R
                f1 = 2 * (p * r) / (p + r) if (p + r) > 0 else 0.0

            results[sec] = {"precision": p, "recall": r, "f1": f1}
        
        return results

    def compute_overall_metrics(self, section_results: Dict) -> Dict:
        # Simple weighted average of F1 for the mock
        f1_scores = [res["f1"] for res in section_results.values()]
        overall_f1 = np.mean(f1_scores) if f1_scores else 0.0
        
        # NOTE: In a real system, overall P/R/F1 would be calculated from the total True/False Positives/Negatives.
        # Here we just use the average F1 as a placeholder.
        return {"f1": overall_f1}
        
RESUME_EVALUATOR = MockResumeEvaluator # Use the mock for visualization purposes

# --- Original Configuration/Helpers (Kept for Context) ---
# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TEST_RESUMES_DIR = Path("tests/test_resumes")
TEST_PAIRS = [
    "ADVOCATE_14445309",
    "BUSINESS-DEVELOPMENT_65708020",
    "DESIGNER_37058472",
    "INFORMATION-TECHNOLOGY_36856210",
    "TEACHER_12467531"
]

def short_id(name: str) -> str:
    """Shorten resume ID for plotting"""
    prefix = name.split("_")[0][:3].upper()
    number = name.split("_")[1][:4] if "_" in name else ""
    return f"{prefix}_{number}" if number else prefix

def load_resume_json(resume_id: str) -> Dict:
    """Mock load function - returns a dict with ID for the mock evaluator"""
    return {"meta": {"id": resume_id}} # Mock structure

def compute_pairwise_metrics(resume_ids: List[str], evaluator: RESUME_EVALUATOR) -> Dict:
    """
    Returns a nested dict:
    results_matrix[A][B] = evaluation metrics when comparing resume A (GT) with B (Pred)
    """
    results_matrix = {}

    # Preload all resumes JSON
    # In a real setup, this would load the actual JSON data for GT and Pred
    resumes_json = {rid: load_resume_json(rid) for rid in resume_ids}

    for A in resume_ids:
        results_matrix[A] = {}
        gt_A = resumes_json[A]

        for B in resume_ids:
            pred_B = resumes_json[B]  # self or others
            section_results = evaluator.evaluate_resume(gt_A, pred_B)
            overall = evaluator.compute_overall_metrics(section_results)

            results_matrix[A][B] = {
                "overall": overall,
                "section_results": section_results
            }
    return results_matrix

# --- REVISED Visualization Function ---

def plot_heatmap_with_annotations(ax: plt.Axes, matrix: np.ndarray, labels: List[str], title: str, cmap: str = "Blues"):
    """Plots a heatmap with annotated F1 scores."""
    n = len(labels)
    im = ax.imshow(matrix, cmap=cmap, vmin=0, vmax=1)
    
    # Set Ticks and Labels
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)
    ax.set_title(title, pad=20)
    
    # Annotate values
    for i in range(n):
        for j in range(n):
            value = matrix[i, j]
            # Choose text color based on background color for contrast
            text_color = "black" if value < 0.5 else "white"
            ax.text(j, i, f'{value:.2f}', ha="center", va="center", color=text_color, fontsize=10)
    
    # Add Colorbar
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

def plot_section_bar_chart(ax: plt.Axes, section_metrics: Dict[str, Tuple[float, float, float]]):
    """Plots corrected Precision, Recall, and F1 per section."""
    sections = list(section_metrics.keys())
    N = len(sections)
    x = np.arange(N)
    width = 0.25

    precisions = [metrics[0] for metrics in section_metrics.values()]
    recalls = [metrics[1] for metrics in section_metrics.values()]
    f1s = [metrics[2] for metrics in section_metrics.values()]
    
    # Plot bars
    bar_p = ax.bar(x - width, precisions, width, label="Precision (P)", color='tab:blue')
    bar_r = ax.bar(x, recalls, width, label="Recall (R)", color='tab:orange')
    bar_f1 = ax.bar(x + width, f1s, width, label="F1-Score", color='tab:green')
    
    ax.set_xticks(x)
    ax.set_xticklabels(sections, rotation=45, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_title("Average Section Performance (Precision, Recall, F1)", pad=15)
    ax.legend(loc='lower right')
    ax.grid(axis='y', linestyle='--', alpha=0.7)

def visualize_metrics_revised(resume_ids: List[str], results_matrix: Dict):
    short_names = [short_id(r) for r in resume_ids]
    n = len(resume_ids)

    # --- Data Compilation ---
    overall_matrix = np.zeros((n, n))
    section_matrices = {}
    
    # Get all section names from one result entry
    if results_matrix:
        sample_result = next(iter(next(iter(results_matrix.values())).values()))
        section_names = list(sample_result["section_results"].keys())
        section_matrices = {sec: {"f1": np.zeros((n, n)), "p": np.zeros((n, n)), "r": np.zeros((n, n))} for sec in section_names}
    else:
        section_names = []
    
    # 1. Populate matrices and calculate global section averages for P/R/F1
    all_section_data = {sec: {"p": [], "r": [], "f1": []} for sec in section_names}

    for i, A in enumerate(resume_ids):
        for j, B in enumerate(resume_ids):
            overall_matrix[i, j] = results_matrix[A][B]["overall"]["f1"]
            for sec in section_names:
                sec_res = results_matrix[A][B]["section_results"].get(sec, {"f1": 0.0, "precision": 0.0, "recall": 0.0})
                
                # Store for Heatmaps
                section_matrices[sec]["f1"][i, j] = sec_res["f1"]
                
                # Store for Averages (only use comparison metrics, not self-comparison)
                if A != B: 
                    all_section_data[sec]["p"].append(sec_res["precision"])
                    all_section_data[sec]["r"].append(sec_res["recall"])
                    all_section_data[sec]["f1"].append(sec_res["f1"])

    # Calculate average P/R/F1 per section (excluding self-comparisons)
    avg_section_metrics = {}
    for sec in section_names:
        data = all_section_data[sec]
        avg_p = np.mean(data["p"]) if data["p"] else 0.0
        avg_r = np.mean(data["r"]) if data["r"] else 0.0
        avg_f1 = np.mean(data["f1"]) if data["f1"] else 0.0
        avg_section_metrics[sec] = (avg_p, avg_r, avg_f1)


    # --- Plotting (Revised Layout) ---
    fig = plt.figure(figsize=(18, 12))
    # Use a 2x3 grid: Bar Chart, Heatmap, Radar Chart, and 3 detail heatmaps
    gs = fig.add_gridspec(2, 3, height_ratios=[1.2, 1], wspace=0.3, hspace=0.4)

    # 1. Section Performance Bar Chart (Top Left)
    ax0 = fig.add_subplot(gs[0, 0])
    plot_section_bar_chart(ax0, avg_section_metrics)

    # 2. Overall Heatmap with Annotations (Top Middle)
    ax1 = fig.add_subplot(gs[0, 1])
    plot_heatmap_with_annotations(ax1, overall_matrix, short_names, "Overall Resume Similarity (Pairwise F1)")
    
    # 3. Radar chart: average per-section F1 (Top Right)
    radar_f1_values = [metrics[2] for metrics in avg_section_metrics.values()]
    N = len(section_names)
    radar_values = radar_f1_values + radar_f1_values[:1]  # close loop
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    ax_radar = fig.add_subplot(gs[0, 2], polar=True)
    ax_radar.plot(angles, radar_values, linewidth=2, linestyle='solid', color='tab:red')
    ax_radar.fill(angles, radar_values, color='tab:red', alpha=0.25)
    
    # Set tick labels
    ax_radar.set_xticks(angles[:-1])
    ax_radar.set_xticklabels(section_names, size=10)
    
    # Set radial axis limits
    ax_radar.set_yticks(np.arange(0, 1.1, 0.2))
    ax_radar.set_yticklabels([f'{x:.1f}' for x in np.arange(0, 1.1, 0.2)], color="grey", size=8)
    ax_radar.set_ylim(0, 1.0)
    
    ax_radar.set_title("Average Section F1 Scores (Consistency)", pad=20)
    
    # 4. Detail Heatmaps (Bottom Row - Focus on high-value sections)
    
    # Select key sections to show detail for (e.g., the 3 highest average F1 sections)
    sorted_sections = sorted(avg_section_metrics.items(), key=lambda item: item[1][2], reverse=True)
    detail_sections = [sec[0] for sec in sorted_sections[:3]]

    for idx, sec in enumerate(detail_sections):
        ax = fig.add_subplot(gs[1, idx])
        plot_heatmap_with_annotations(ax, section_matrices[sec]["f1"], short_names, f"{sec.title()} Section F1", cmap="viridis")
        ax.set_xticks([]) # Remove ticks for a cleaner look in details
        ax.set_yticks([]) 
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.set_xlabel("Predicted Resume (B)")
        ax.set_ylabel("Ground Truth (A)")

    plt.tight_layout(rect=[0, 0, 1, 0.98]) # Adjust for suptitle
    fig.suptitle("Revised Resume Evaluation Dashboard", fontsize=16, fontweight='bold')
    plt.savefig("eval_revised.png")
    logger.info("Revised visualization saved to eval_revised.png")

# --- Main ---
def main():
    logger.info("Initializing FullResumeEvaluator (Mock)")
    evaluator = RESUME_EVALUATOR()

    logger.info("Computing pairwise metrics...")
    results_matrix = compute_pairwise_metrics(TEST_PAIRS, evaluator)

    logger.info("Generating revised combined visualization...")
    visualize_metrics_revised(TEST_PAIRS, results_matrix)

if __name__ == "__main__":
    main()