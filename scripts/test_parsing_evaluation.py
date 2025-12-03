#!/usr/bin/env python3
"""
Test script for evaluating PDF parsing quality using PDF-JSON pairs.

This script:
1. Loads test resume PDF-JSON pairs from tests/test_resumes/
2. Parses each PDF using the LangGraph parser
3. Evaluates against ground truth JSON using the Hungarian evaluation method
4. Generates a comprehensive results table for LaTeX inclusion

Usage:
    python scripts/test_parsing_evaluation.py
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.parsing.extractors.naive.pdf_parser_langgraph import PDFParserLangGraph
from core.parsing.evaluators.main import RESUME_EVALUATOR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Test resume pairs
TEST_RESUMES_DIR = Path("tests/test_resumes")

TEST_PAIRS = [
    "ADVOCATE_14445309",
    "BUSINESS-DEVELOPMENT_65708020",
    "DESIGNER_37058472",
    "INFORMATION-TECHNOLOGY_36856210",
    "TEACHER_12467531"
]


def load_ground_truth(resume_id: str) -> Dict:
    """Load ground truth JSON for a resume"""
    json_path = TEST_RESUMES_DIR / f"{resume_id}.json"
    with open(json_path, 'r') as f:
        return json.load(f)


def parse_resume(resume_id: str, parser: PDFParserLangGraph) -> Dict:
    """Parse a resume PDF and return the result"""
    pdf_path = TEST_RESUMES_DIR / f"{resume_id}.pdf"
    logger.info(f"\n{'='*60}")
    logger.info(f"Parsing: {resume_id}")
    logger.info(f"{'='*60}")

    result = parser.parse(pdf_path)

    if "error" in result:
        logger.error(f"Parsing failed: {result['error']}")
        return {}

    return result


def evaluate_resume(resume_id: str, ground_truth: Dict, predicted: Dict) -> Dict:
    """Evaluate predicted resume against ground truth"""
    logger.info(f"\nEvaluating: {resume_id}")

    section_results = RESUME_EVALUATOR.evaluate_resume(ground_truth, predicted)
    overall_metrics = RESUME_EVALUATOR.compute_overall_metrics(section_results)

    return {
        "resume_id": resume_id,
        "section_results": section_results,
        "overall": overall_metrics
    }


def format_section_summary(section_results: Dict) -> str:
    """Format section results for display"""
    summary = []
    for section, metrics in section_results.items():
        if metrics.get("precision", 0) > 0 or metrics.get("recall", 0) > 0:
            summary.append(f"{section}: P={metrics['precision']:.2f} R={metrics['recall']:.2f} F1={metrics['f1']:.2f}")
    return "\n".join(summary)


def generate_latex_table(all_results: List[Dict]) -> str:
    """Generate LaTeX table from results"""
    latex = []
    latex.append("\\begin{table}[h]")
    latex.append("\\centering")
    latex.append("\\caption{Resume Parsing Evaluation Results using LangGraph Parser}")
    latex.append("\\label{tab:parsing-eval}")
    latex.append("\\begin{tabular}{|l|c|c|c|c|c|}")
    latex.append("\\hline")
    latex.append("\\textbf{Resume} & \\textbf{Precision} & \\textbf{Recall} & \\textbf{F1} & \\textbf{Field Acc.} & \\textbf{Sections} \\\\")
    latex.append("\\hline")

    for result in all_results:
        overall = result["overall"]
        resume_id = result["resume_id"].replace("_", "\\_")
        precision = overall["precision"]
        recall = overall["recall"]
        f1 = overall["f1"]
        field_acc = overall["avg_field_accuracy"]
        sections = overall["sections_evaluated"]

        latex.append(f"{resume_id} & {precision:.3f} & {recall:.3f} & {f1:.3f} & {field_acc:.3f} & {sections} \\\\")

    latex.append("\\hline")

    # Calculate averages
    avg_precision = sum(r["overall"]["precision"] for r in all_results) / len(all_results)
    avg_recall = sum(r["overall"]["recall"] for r in all_results) / len(all_results)
    avg_f1 = sum(r["overall"]["f1"] for r in all_results) / len(all_results)
    avg_field_acc = sum(r["overall"]["avg_field_accuracy"] for r in all_results) / len(all_results)

    latex.append(f"\\textbf{{Average}} & \\textbf{{{avg_precision:.3f}}} & \\textbf{{{avg_recall:.3f}}} & \\textbf{{{avg_f1:.3f}}} & \\textbf{{{avg_field_acc:.3f}}} & - \\\\")
    latex.append("\\hline")
    latex.append("\\end{tabular}")
    latex.append("\\end{table}")

    return "\n".join(latex)


def generate_detailed_section_table(all_results: List[Dict]) -> str:
    """Generate detailed per-section performance table"""
    # Collect all section names
    all_sections = set()
    for result in all_results:
        all_sections.update(result["section_results"].keys())

    all_sections = sorted(all_sections)

    latex = []
    latex.append("\\begin{table}[h]")
    latex.append("\\centering")
    latex.append("\\caption{Per-Section F1 Scores Across Test Resumes}")
    latex.append("\\label{tab:section-f1}")
    latex.append("\\begin{tabular}{|l|" + "c|" * len(all_results) + "c|}")
    latex.append("\\hline")

    # Header row
    header = "\\textbf{Section} & " + " & ".join([f"\\textbf{{{r['resume_id'].split('_')[0]}}}" for r in all_results])
    header += " & \\textbf{Avg} \\\\"
    latex.append(header)
    latex.append("\\hline")

    # Section rows
    for section in all_sections:
        f1_scores = []
        row = section.capitalize()

        for result in all_results:
            f1 = result["section_results"].get(section, {}).get("f1", 0.0)
            f1_scores.append(f1)
            row += f" & {f1:.2f}"

        avg_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
        row += f" & \\textbf{{{avg_f1:.2f}}} \\\\"
        latex.append(row)

    latex.append("\\hline")
    latex.append("\\end{tabular}")
    latex.append("\\end{table}")

    return "\n".join(latex)


def main():
    """Main evaluation script"""
    logger.info("Starting Resume Parsing Evaluation")
    logger.info(f"Test resumes directory: {TEST_RESUMES_DIR}")
    logger.info(f"Number of test pairs: {len(TEST_PAIRS)}")

    # Initialize parser
    logger.info("\nInitializing LangGraph PDF Parser...")
    parser = PDFParserLangGraph()

    # Run evaluations
    all_results = []

    for resume_id in TEST_PAIRS:
        try:
            # Load ground truth
            ground_truth = load_ground_truth(resume_id)

            # Parse PDF
            predicted = parse_resume(resume_id, parser)

            if not predicted:
                logger.warning(f"Skipping {resume_id} due to parsing failure")
                continue

            # Evaluate
            eval_result = evaluate_resume(resume_id, ground_truth, predicted)
            all_results.append(eval_result)

            # Print summary
            logger.info(f"\n--- Results for {resume_id} ---")
            logger.info(f"Overall Precision: {eval_result['overall']['precision']:.3f}")
            logger.info(f"Overall Recall: {eval_result['overall']['recall']:.3f}")
            logger.info(f"Overall F1: {eval_result['overall']['f1']:.3f}")
            logger.info(f"Avg Field Accuracy: {eval_result['overall']['avg_field_accuracy']:.3f}")
            logger.info(f"Sections Evaluated: {eval_result['overall']['sections_evaluated']}")

        except Exception as e:
            logger.error(f"Error processing {resume_id}: {e}", exc_info=True)
            continue

    # Generate summary table
    if all_results:
        logger.info("\n" + "="*60)
        logger.info("OVERALL SUMMARY")
        logger.info("="*60)

        # Console table
        table_data = []
        for result in all_results:
            table_data.append([
                result["resume_id"],
                f"{result['overall']['precision']:.3f}",
                f"{result['overall']['recall']:.3f}",
                f"{result['overall']['f1']:.3f}",
                f"{result['overall']['avg_field_accuracy']:.3f}",
                result['overall']['sections_evaluated']
            ])

        # Add averages
        avg_precision = sum(r["overall"]["precision"] for r in all_results) / len(all_results)
        avg_recall = sum(r["overall"]["recall"] for r in all_results) / len(all_results)
        avg_f1 = sum(r["overall"]["f1"] for r in all_results) / len(all_results)
        avg_field_acc = sum(r["overall"]["avg_field_accuracy"] for r in all_results) / len(all_results)

        table_data.append([
            "AVERAGE",
            f"{avg_precision:.3f}",
            f"{avg_recall:.3f}",
            f"{avg_f1:.3f}",
            f"{avg_field_acc:.3f}",
            "-"
        ])

        # Print simple table
        print("\n{:<40} {:<12} {:<12} {:<12} {:<12} {:<10}".format(
            "Resume", "Precision", "Recall", "F1", "Field Acc.", "Sections"
        ))
        print("-" * 100)
        for row in table_data:
            print("{:<40} {:<12} {:<12} {:<12} {:<12} {:<10}".format(*row))

        # Generate LaTeX tables
        logger.info("\n" + "="*60)
        logger.info("LATEX TABLE OUTPUT")
        logger.info("="*60)

        latex_table = generate_latex_table(all_results)
        print("\n" + latex_table)

        section_table = generate_detailed_section_table(all_results)
        print("\n" + section_table)

        # Save to file
        output_file = Path("scripts/evaluation_results_latex.tex")
        with open(output_file, 'w') as f:
            f.write("% Overall Results Table\n")
            f.write(latex_table)
            f.write("\n\n% Per-Section Results Table\n")
            f.write(section_table)

        logger.info(f"\nLaTeX tables saved to: {output_file}")

        # Save detailed JSON results
        json_output = Path("scripts/evaluation_results.json")
        with open(json_output, 'w') as f:
            json.dump(all_results, f, indent=2)

        logger.info(f"Detailed JSON results saved to: {json_output}")

    else:
        logger.error("No results to report!")


if __name__ == "__main__":
    main()
