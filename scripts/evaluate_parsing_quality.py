"""
Evaluate CV parsing quality using ground truth labeled CVs.
Provides metrics on parsing accuracy without relying on user feedback.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.parsing.extractors.naive.pdf_parser import parse_resume_with_llm
from core.parsing.schema import Resume
import json
from typing import Dict, List, Any
import re
from datetime import datetime


class ParsingQualityEvaluator:
    """Evaluates CV parsing quality using multiple metrics."""

    def __init__(self, ground_truth_dir: str = "tests/test_resumes"):
        self.ground_truth_dir = Path(ground_truth_dir)

    def validate_schema(self, parsed_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Validate that parsed data conforms to expected schema.
        Returns completeness and validity scores.
        """
        # Required fields
        required_fields = {
            "basics": ["name", "email"],
            "work": ["name", "position"],
            "education": ["institution", "area"],
            "skills": ["name"]
        }

        total_fields = 0
        valid_fields = 0

        # Check basics
        if "basics" in parsed_data and parsed_data["basics"]:
            basics = parsed_data["basics"]
            for field in required_fields["basics"]:
                total_fields += 1
                if field in basics and basics[field]:
                    valid_fields += 1

        # Check work
        if "work" in parsed_data and parsed_data["work"]:
            for work_item in parsed_data["work"]:
                for field in required_fields["work"]:
                    total_fields += 1
                    if field in work_item and work_item[field]:
                        valid_fields += 1

        # Check education
        if "education" in parsed_data and parsed_data["education"]:
            for edu_item in parsed_data["education"]:
                for field in required_fields["education"]:
                    total_fields += 1
                    if field in edu_item and edu_item[field]:
                        valid_fields += 1

        # Check skills
        if "skills" in parsed_data and parsed_data["skills"]:
            skills_count = len(parsed_data["skills"])
            total_fields += 1
            if skills_count > 0:
                valid_fields += 1

        completeness_score = valid_fields / total_fields if total_fields > 0 else 0

        return {
            "completeness_score": completeness_score,
            "total_fields": total_fields,
            "valid_fields": valid_fields
        }

    def validate_field_formats(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate field formats using regex and heuristics.
        """
        issues = []
        validations = {
            "email_valid": False,
            "phone_valid": False,
            "dates_valid": True,
            "skills_count": 0
        }

        # Validate email
        if "basics" in parsed_data and "email" in parsed_data["basics"]:
            email = parsed_data["basics"]["email"]
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if re.match(email_pattern, email):
                validations["email_valid"] = True
            else:
                issues.append(f"Invalid email format: {email}")

        # Validate phone
        if "basics" in parsed_data and "phone" in parsed_data["basics"]:
            phone = parsed_data["basics"]["phone"]
            # Simple validation (contains digits)
            if phone and any(char.isdigit() for char in phone):
                validations["phone_valid"] = True

        # Validate dates in work history
        if "work" in parsed_data:
            for work_item in parsed_data["work"]:
                start_date = work_item.get("startDate", "")
                end_date = work_item.get("endDate", "")

                # Check date format (YYYY-MM-DD or YYYY)
                if start_date and not self._is_valid_date(start_date):
                    issues.append(f"Invalid start date format: {start_date}")
                    validations["dates_valid"] = False

                if end_date and end_date.lower() != "present" and not self._is_valid_date(end_date):
                    issues.append(f"Invalid end date format: {end_date}")
                    validations["dates_valid"] = False

                # Check start < end
                if start_date and end_date and end_date.lower() != "present":
                    if not self._is_date_before(start_date, end_date):
                        issues.append(f"Start date {start_date} is after end date {end_date}")
                        validations["dates_valid"] = False

        # Count skills
        if "skills" in parsed_data:
            validations["skills_count"] = len(parsed_data["skills"])

        validations["issues"] = issues
        return validations

    def _is_valid_date(self, date_str: str) -> bool:
        """Check if date string is in valid format."""
        patterns = [
            r'^\d{4}$',  # YYYY
            r'^\d{4}-\d{2}$',  # YYYY-MM
            r'^\d{4}-\d{2}-\d{2}$'  # YYYY-MM-DD
        ]
        return any(re.match(pattern, date_str) for pattern in patterns)

    def _is_date_before(self, date1: str, date2: str) -> bool:
        """Check if date1 is before date2."""
        try:
            # Extract year for simple comparison
            year1 = int(date1[:4])
            year2 = int(date2[:4])
            return year1 <= year2
        except:
            return True  # If can't parse, don't flag as error

    def check_cross_field_consistency(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check consistency across fields.
        """
        issues = []
        checks = {
            "no_duplicates": True,
            "experience_plausible": True
        }

        # Check for duplicate work entries
        if "work" in parsed_data:
            companies = [w.get("name", "") for w in parsed_data["work"]]
            if len(companies) != len(set(companies)):
                issues.append("Duplicate company entries detected")
                checks["no_duplicates"] = False

        # Check total experience is plausible (< 50 years)
        total_years = self._calculate_total_experience(parsed_data)
        if total_years > 50:
            issues.append(f"Implausible total experience: {total_years} years")
            checks["experience_plausible"] = False

        checks["issues"] = issues
        return checks

    def _calculate_total_experience(self, parsed_data: Dict[str, Any]) -> float:
        """Calculate total years of experience."""
        total_months = 0

        if "work" not in parsed_data:
            return 0

        for work_item in parsed_data["work"]:
            start_date = work_item.get("startDate", "")
            end_date = work_item.get("endDate", "Present")

            if not start_date:
                continue

            try:
                start_year = int(start_date[:4])
                if end_date.lower() == "present":
                    end_year = datetime.now().year
                else:
                    end_year = int(end_date[:4])

                years = end_year - start_year
                total_months += years * 12
            except:
                continue

        return total_months / 12.0

    def compare_with_ground_truth(self, parsed_data: Dict[str, Any], ground_truth: Dict[str, Any]) -> Dict[str, float]:
        """
        Compare parsed data against manually labeled ground truth.
        Returns precision, recall, and F1 scores for key fields.
        """
        metrics = {}

        # Compare name
        parsed_name = parsed_data.get("basics", {}).get("name", "").lower()
        gt_name = ground_truth.get("basics", {}).get("name", "").lower()
        metrics["name_match"] = 1.0 if parsed_name == gt_name else 0.0

        # Compare email
        parsed_email = parsed_data.get("basics", {}).get("email", "").lower()
        gt_email = ground_truth.get("basics", {}).get("email", "").lower()
        metrics["email_match"] = 1.0 if parsed_email == gt_email else 0.0

        # Compare skills (Precision, Recall, F1)
        parsed_skills = set([s.get("name", "").lower() for s in parsed_data.get("skills", [])])
        gt_skills = set([s.get("name", "").lower() for s in ground_truth.get("skills", [])])

        if gt_skills:
            true_positives = len(parsed_skills & gt_skills)
            false_positives = len(parsed_skills - gt_skills)
            false_negatives = len(gt_skills - parsed_skills)

            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            metrics["skills_precision"] = precision
            metrics["skills_recall"] = recall
            metrics["skills_f1"] = f1
        else:
            metrics["skills_precision"] = 0
            metrics["skills_recall"] = 0
            metrics["skills_f1"] = 0

        return metrics

    def evaluate_cv(self, cv_path: Path, ground_truth_path: Path = None) -> Dict[str, Any]:
        """
        Evaluate a single CV file.
        """
        print(f"\n📄 Evaluating: {cv_path.name}")

        # Parse CV
        try:
            parsed_data = parse_resume_with_llm(str(cv_path))
        except Exception as e:
            print(f"❌ Parsing failed: {e}")
            return {"status": "failed", "error": str(e)}

        # Schema validation
        schema_results = self.validate_schema(parsed_data)
        print(f"   Completeness: {schema_results['completeness_score']:.2%}")

        # Format validation
        format_results = self.validate_field_formats(parsed_data)
        print(f"   Email valid: {format_results['email_valid']}")
        print(f"   Dates valid: {format_results['dates_valid']}")
        print(f"   Skills found: {format_results['skills_count']}")

        # Consistency checks
        consistency_results = self.check_cross_field_consistency(parsed_data)
        print(f"   No duplicates: {consistency_results['no_duplicates']}")
        print(f"   Experience plausible: {consistency_results['experience_plausible']}")

        # Ground truth comparison (if available)
        gt_results = {}
        if ground_truth_path and ground_truth_path.exists():
            with open(ground_truth_path) as f:
                ground_truth = json.load(f)
            gt_results = self.compare_with_ground_truth(parsed_data, ground_truth)
            print(f"   Name match: {gt_results.get('name_match', 0):.2%}")
            print(f"   Skills F1: {gt_results.get('skills_f1', 0):.2%}")

        return {
            "status": "success",
            "cv_path": str(cv_path),
            "schema": schema_results,
            "format": format_results,
            "consistency": consistency_results,
            "ground_truth": gt_results
        }

    def evaluate_batch(self) -> Dict[str, Any]:
        """
        Evaluate all CVs in the ground truth directory.
        """
        print(f"\n🔍 Evaluating CVs in: {self.ground_truth_dir}\n")

        cv_files = list(self.ground_truth_dir.glob("*.pdf"))

        if not cv_files:
            print("❌ No PDF files found")
            return {"status": "no_files"}

        results = []
        for cv_file in cv_files:
            # Check for corresponding ground truth JSON
            gt_file = cv_file.with_suffix(".json")
            result = self.evaluate_cv(cv_file, gt_file)
            results.append(result)

        # Aggregate metrics
        successful = [r for r in results if r["status"] == "success"]
        if not successful:
            print("\n❌ No successful parses")
            return {"status": "no_success", "results": results}

        avg_completeness = sum(r["schema"]["completeness_score"] for r in successful) / len(successful)
        avg_email_valid = sum(r["format"]["email_valid"] for r in successful) / len(successful)
        avg_dates_valid = sum(r["format"]["dates_valid"] for r in successful) / len(successful)

        print(f"\n📊 Aggregate Metrics ({len(successful)} CVs)")
        print(f"   Average Completeness: {avg_completeness:.2%}")
        print(f"   Email Validity: {avg_email_valid:.2%}")
        print(f"   Date Validity: {avg_dates_valid:.2%}")

        # Ground truth metrics (if available)
        gt_results = [r["ground_truth"] for r in successful if r["ground_truth"]]
        if gt_results:
            avg_skills_f1 = sum(r.get("skills_f1", 0) for r in gt_results) / len(gt_results)
            print(f"   Average Skills F1: {avg_skills_f1:.2%}")

        return {
            "status": "success",
            "total_cvs": len(cv_files),
            "successful_parses": len(successful),
            "average_completeness": avg_completeness,
            "average_email_valid": avg_email_valid,
            "average_dates_valid": avg_dates_valid,
            "results": results
        }


def main():
    """Main evaluation function."""
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate CV parsing quality")
    parser.add_argument("--dir", default="tests/test_resumes", help="Directory with test CVs")
    parser.add_argument("--cv", help="Evaluate single CV file")

    args = parser.parse_args()

    evaluator = ParsingQualityEvaluator(ground_truth_dir=args.dir)

    if args.cv:
        # Evaluate single CV
        cv_path = Path(args.cv)
        result = evaluator.evaluate_cv(cv_path)
        print(f"\n✅ Evaluation complete")
    else:
        # Evaluate batch
        result = evaluator.evaluate_batch()
        print(f"\n✅ Batch evaluation complete")

    # Save results
    output_file = Path("parsing_evaluation_results.json")
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    main()
