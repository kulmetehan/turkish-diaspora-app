#!/usr/bin/env python3
"""
Script to update plan document status after completing tasks.

Usage:
    python scripts/update_plan_status.py --plan claim-consent-outreach-implementation-plan.md --step "7.3" --completed
    python scripts/update_plan_status.py --plan claim-consent-outreach-implementation-plan.md --step "Stap 7.3" --completed
"""

import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import List, Tuple


def find_step_in_content(content: str, step_identifier: str) -> Tuple[int, int, str]:
    """
    Find a step in the plan document content.
    
    Args:
        content: The full content of the plan document
        step_identifier: Step identifier like "7.3" or "Stap 7.3"
    
    Returns:
        Tuple of (start_line_index, end_line_index, step_section)
    """
    # Normalize step identifier - remove "Stap" prefix if present
    step_num = step_identifier.replace("Stap", "").strip()
    
    # Try different patterns to find the step
    patterns = [
        rf"####\s+Stap\s+{re.escape(step_num)}",
        rf"###\s+Stap\s+{re.escape(step_num)}",
        rf"####\s+{re.escape(step_num)}",
        rf"###\s+{re.escape(step_num)}",
    ]
    
    lines = content.split('\n')
    
    for pattern in patterns:
        for i, line in enumerate(lines):
            if re.search(pattern, line, re.IGNORECASE):
                # Found the step header, find the end (next header at same or higher level)
                start_idx = i
                
                # Find the end - next header at same level (####) or higher level (###, ##, #)
                end_idx = len(lines)
                header_level = len(line) - len(line.lstrip('#'))
                
                for j in range(i + 1, len(lines)):
                    if lines[j].strip().startswith('#'):
                        current_level = len(lines[j]) - len(lines[j].lstrip('#'))
                        if current_level <= header_level:
                            end_idx = j
                            break
                
                step_section = '\n'.join(lines[start_idx:end_idx])
                return start_idx, end_idx, step_section
    
    return -1, -1, ""


def update_checkbox_in_section(section: str, step_identifier: str) -> str:
    """
    Update checkbox in a step section to mark it as completed.
    
    Args:
        section: The step section content
        step_identifier: Step identifier
    
    Returns:
        Updated section with checkbox marked as completed
    """
    # Find checkbox patterns like "- [ ] **Stap X.Y**:"
    # Replace with "- [x] **Stap X.Y**:"
    patterns = [
        rf"(- \[ \])\s+\*\*Stap\s+{re.escape(step_identifier.replace('Stap', '').strip())}",
        rf"(- \[ \])\s+\*\*{re.escape(step_identifier.replace('Stap', '').strip())}",
    ]
    
    updated_section = section
    for pattern in patterns:
        updated_section = re.sub(
            pattern,
            r"- [x] **Stap " + step_identifier.replace('Stap', '').strip() + "**",
            updated_section,
            flags=re.IGNORECASE
        )
    
    # Also update any checkbox in the "Acceptatie Criteria" section
    # Pattern: "- [ ] Some criterion"
    lines = updated_section.split('\n')
    in_acceptatie = False
    for i, line in enumerate(lines):
        if 'Acceptatie Criteria' in line or 'acceptatie criteria' in line.lower():
            in_acceptatie = True
        elif line.strip().startswith('**') or line.strip().startswith('#'):
            in_acceptatie = False
        
        if in_acceptatie and re.match(r'^\s*-\s+\[ \]', line):
            lines[i] = re.sub(r'^\s*-\s+\[ \]', r'- [x]', line)
    
    return '\n'.join(lines)


def update_last_update_date(content: str) -> str:
    """
    Update the "Laatste Update" date in the plan document.
    
    Args:
        content: The full content of the plan document
    
    Returns:
        Updated content with new date
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Pattern: **Laatste Update**: YYYY-MM-DD
    pattern = r'\*\*Laatste Update\*\*:\s*\d{4}-\d{2}-\d{2}'
    replacement = f"**Laatste Update**: {today}"
    
    updated = re.sub(pattern, replacement, content)
    return updated


def update_status_tracking(content: str, step_identifier: str) -> str:
    """
    Update the status tracking section to include the completed step.
    
    Args:
        content: The full content of the plan document
        step_identifier: Step identifier like "7.3"
    
    Returns:
        Updated content
    """
    # Find the status tracking section
    # Pattern: "**Laatste Update**: ... (Stap X.Y, ... voltooid)"
    pattern = r'(\*\*Laatste Update\*\*:\s*\d{4}-\d{2}-\d{2}\s*\([^)]+\))'
    
    def replace_status(match):
        status_text = match.group(1)
        # Extract existing steps
        if step_identifier.replace('Stap', '').strip() not in status_text:
            # Add step to the list
            # Pattern: (Stap X.Y, ... voltooid)
            if 'voltooid' in status_text:
                # Add to existing list
                status_text = status_text.replace(' voltooid)', f", {step_identifier.replace('Stap', '').strip()} voltooid)")
            else:
                # First step
                status_text = status_text.replace(')', f" ({step_identifier.replace('Stap', '').strip()} voltooid)")
        return status_text
    
    updated = re.sub(pattern, replace_status, content)
    return updated


def update_plan_document(plan_path: Path, step_identifier: str, status: str):
    """
    Update the plan document with the new status.
    
    Args:
        plan_path: Path to the plan document
        step_identifier: Step identifier like "7.3" or "Stap 7.3"
        status: Status to set ("completed" or "in_progress")
    """
    if not plan_path.exists():
        print(f"Error: Plan document not found at {plan_path}")
        return
    
    # Read the plan document
    with open(plan_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the step section
    start_idx, end_idx, step_section = find_step_in_content(content, step_identifier)
    
    if start_idx == -1:
        print(f"Warning: Step {step_identifier} not found in plan document")
        print("Attempting to update status tracking section anyway...")
    else:
        # Update the step section
        updated_section = update_checkbox_in_section(step_section, step_identifier)
        
        # Replace the section in the content
        lines = content.split('\n')
        new_lines = lines[:start_idx] + updated_section.split('\n') + lines[end_idx:]
        content = '\n'.join(new_lines)
    
    # Update last update date
    content = update_last_update_date(content)
    
    # Update status tracking section
    if status == "completed":
        content = update_status_tracking(content, step_identifier)
    
    # Write back to file
    with open(plan_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Updated plan document: {plan_path}")
    print(f"  Step: {step_identifier}")
    print(f"  Status: {status}")


def main():
    parser = argparse.ArgumentParser(
        description="Update plan document status after completing tasks"
    )
    parser.add_argument(
        "--plan",
        type=str,
        required=True,
        help="Plan document filename (e.g., claim-consent-outreach-implementation-plan.md)"
    )
    parser.add_argument(
        "--step",
        type=str,
        required=True,
        help="Step identifier (e.g., '7.3' or 'Stap 7.3')"
    )
    parser.add_argument(
        "--status",
        type=str,
        choices=["completed", "in_progress"],
        default="completed",
        help="Status to set (default: completed)"
    )
    
    args = parser.parse_args()
    
    # Find plan document in Docs directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    docs_dir = project_root / "Docs"
    plan_path = docs_dir / args.plan
    
    if not plan_path.exists():
        print(f"Error: Plan document not found at {plan_path}")
        print(f"  Searched in: {docs_dir}")
        return 1
    
    update_plan_document(plan_path, args.step, args.status)
    return 0


if __name__ == "__main__":
    exit(main())

