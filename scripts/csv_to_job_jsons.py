"""
Parse tiny.csv and create individual JSON files for each job posting.
Each JSON file is named with the Job ID and contains all job details.
"""

import csv
import json
import ast
from pathlib import Path
from typing import Dict, Any, List, Optional


class JobJSONGenerator:
    """Converts CSV job data to individual JSON files."""

    def __init__(self, csv_path: str, output_dir: str):
        """
        Initialize the generator.
        
        Args:
            csv_path: Path to the tiny.csv file
            output_dir: Directory to save JSON files
        """
        self.csv_path = Path(csv_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def parse_string_list(self, value: str) -> Optional[List[str]]:
        """Parse a string representation of a list or set into a Python list."""
        if not value or value.strip() == '':
            return None
        
        try:
            # Handle set notation like "{'item1, item2, item3'}"
            if value.startswith('{') and value.endswith('}'):
                # Remove outer braces and quotes
                content = value[1:-1].strip()
                if content.startswith("'") and content.endswith("'"):
                    content = content[1:-1]
                # Split by comma
                items = [item.strip() for item in content.split(',')]
                return items if items else None
            
            # Try to evaluate as Python literal
            parsed = ast.literal_eval(value)
            if isinstance(parsed, (list, set)):
                return list(parsed)
            return [str(parsed)]
        except:
            # If all else fails, split by common delimiters
            if ',' in value:
                return [item.strip() for item in value.split(',')]
            return [value.strip()]

    def parse_json_string(self, value: str) -> Optional[Dict]:
        """Parse a JSON string into a dictionary."""
        if not value or value.strip() == '':
            return None
        
        try:
            # Replace double quotes that are escaped
            cleaned = value.replace('""', '"')
            return json.loads(cleaned)
        except:
            return None

    def parse_location(self, city: str, country: str, latitude: str, longitude: str) -> Optional[Dict]:
        """Create a location object from CSV fields."""
        if not city:
            return None
        
        location = {
            "city": city,
            "countryCode": country if country else None
        }
        
        # Add coordinates if available
        try:
            if latitude and longitude:
                location["latitude"] = float(latitude)
                location["longitude"] = float(longitude)
        except ValueError:
            pass
        
        return location

    def parse_skills(self, skills_str: str) -> Optional[List[Dict]]:
        """Parse skills string into list of skill objects."""
        if not skills_str:
            return None
        
        skills_list = self.parse_string_list(skills_str)
        if not skills_list:
            return None
        
        # Convert to skill objects with name field
        return [{"name": skill.strip(), "level": None, "keywords": []} for skill in skills_list if skill.strip()]

    def convert_row_to_job(self, row: Dict[str, str]) -> Dict[str, Any]:
        """
        Convert a CSV row to a job JSON object matching the Job model schema.
        
        Args:
            row: Dictionary containing CSV row data
            
        Returns:
            Dictionary representing the job in JSON format
        """
        # Parse company profile
        company_profile = self.parse_json_string(row.get('Company Profile', ''))
        
        # Parse location
        location = self.parse_location(
            row.get('location', ''),
            row.get('Country', ''),
            row.get('latitude', ''),
            row.get('longitude', '')
        )
        
        # Parse skills
        skills = self.parse_skills(row.get('skills', ''))
        
        # Parse benefits
        benefits = self.parse_string_list(row.get('Benefits', ''))
        
        # Parse responsibilities
        responsibilities = self.parse_string_list(row.get('Responsibilities', ''))
        
        # Parse qualifications (convert to list if it's a string)
        qualifications_str = row.get('Qualifications', '')
        qualifications = [qualifications_str] if qualifications_str else None
        
        # Build the job object
        job = {
            # Core required fields
            "job_id": str(row.get('Job Id', '')),
            "title": row.get('Job Title', ''),
            "company": row.get('Company', ''),
            "description": row.get('Job Description', ''),
            
            # Optional standard fields
            "type": row.get('Work Type') if row.get('Work Type') else None,
            "date": row.get('Job Posting Date') if row.get('Job Posting Date') else None,
            "location": location,
            "remote": None,  # Not in CSV
            "salary": row.get('Salary Range') if row.get('Salary Range') else None,
            "experience": row.get('Experience') if row.get('Experience') else None,
            "responsibilities": responsibilities,
            "qualifications": qualifications,
            "skills": skills,
            
            # Extended fields
            "role": row.get('Role') if row.get('Role') else None,
            "salary_range": row.get('Salary Range') if row.get('Salary Range') else None,
            "benefits": benefits,
            "company_size": int(row.get('Company Size')) if row.get('Company Size', '').isdigit() else None,
            "job_posting_date": row.get('Job Posting Date') if row.get('Job Posting Date') else None,
            "preference": row.get('Preference') if row.get('Preference') else None,
            "contact_person": row.get('Contact Person') if row.get('Contact Person') else None,
            "contact": row.get('Contact') if row.get('Contact') else None,
            "job_portal": row.get('Job Portal') if row.get('Job Portal') else None,
            "company_profile": company_profile,
            "country": row.get('Country') if row.get('Country') else None,
            "latitude": float(row.get('latitude')) if row.get('latitude', '').replace('-', '').replace('.', '').isdigit() else None,
            "longitude": float(row.get('longitude')) if row.get('longitude', '').replace('-', '').replace('.', '').isdigit() else None,
        }
        
        # Remove None values for cleaner JSON
        return {k: v for k, v in job.items() if v is not None}

    def generate_json_files(self) -> int:
        """
        Read the CSV file and generate individual JSON files for each job.
        
        Returns:
            Number of JSON files created
        """
        created_count = 0
        
        print(f"📖 Reading CSV file: {self.csv_path}")
        
        with open(self.csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                # Skip empty rows
                if not row.get('Job Id'):
                    continue
                
                try:
                    # Convert row to job JSON
                    job_data = self.convert_row_to_job(row)
                    
                    # Create filename from job_id
                    job_id = job_data['job_id']
                    filename = f"{job_id}.json"
                    filepath = self.output_dir / filename
                    
                    # Write JSON file
                    with open(filepath, 'w', encoding='utf-8') as jsonfile:
                        json.dump(job_data, jsonfile, indent=2, ensure_ascii=False)
                    
                    created_count += 1
                    print(f"✅ Created: {filename}")
                    
                except Exception as e:
                    print(f"❌ Error processing job {row.get('Job Id', 'unknown')}: {e}")
                    continue
        
        return created_count


def main():
    """Main function to generate JSON files from tiny.csv."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate individual JSON files for each job in tiny.csv"
    )
    parser.add_argument(
        "--csv",
        type=str,
        default="core/matching/job_descs/tiny.csv",
        help="Path to the CSV file (default: core/matching/job_descs/tiny.csv)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="core/matching/job_descs",
        help="Output directory for JSON files (default: core/matching/job_descs)"
    )
    
    args = parser.parse_args()
    
    # Get absolute paths
    script_dir = Path(__file__).parent.parent
    csv_path = script_dir / args.csv
    output_dir = script_dir / args.output
    
    # Validate CSV exists
    if not csv_path.exists():
        print(f"❌ Error: CSV file not found at {csv_path}")
        return
    
    # Create generator and process
    generator = JobJSONGenerator(str(csv_path), str(output_dir))
    
    print("\n" + "="*60)
    print("🚀 Starting JSON file generation from tiny.csv")
    print("="*60 + "\n")
    
    count = generator.generate_json_files()
    
    print("\n" + "="*60)
    print(f"✅ Successfully created {count} JSON files")
    print(f"📁 Output directory: {output_dir}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
