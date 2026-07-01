from typing import List, Dict, Any
from app.schemas.assessment import AssessmentResultCreate

class AggregationEngine:
    """
    Compiles child assessments into parent/group compliance statuses.
    """
    
    def aggregate(self, group_id: str, group_title: str, child_results: List[AssessmentResultCreate]) -> AssessmentResultCreate:
        if not child_results:
            return AssessmentResultCreate(
                requirement_id=group_id,
                status="manual_review",
                confidence_score=0.0,
                justification=f"Group {group_id} ({group_title}) has no child requirements evaluated.",
                evidence_references=[]
            )
            
        total_children = len(child_results)
        
        # Count statuses
        status_counts = {
            "compliant": 0,
            "partial": 0,
            "non_compliant": 0,
            "manual_review": 0
        }
        
        for res in child_results:
            if res.status in status_counts:
                status_counts[res.status] += 1
            else:
                status_counts["manual_review"] += 1
                
        # Determine coverage ratio
        covered = status_counts["compliant"]
        partial = status_counts["partial"]
        failed = status_counts["non_compliant"]
        
        # Simple coverage ratio: compliant = 1.0, partial = 0.5
        coverage_ratio = (covered + (partial * 0.5)) / total_children
        
        # Determine overall status
        if failed > 0:
            overall_status = "non_compliant"
        elif partial > 0 or status_counts["manual_review"] > 0:
            overall_status = "partial"
        else:
            overall_status = "compliant"
            
        # Build Summary
        summary_lines = [
            f"**Overall Status**: {overall_status.upper().replace('_', ' ')}",
            f"**Coverage Ratio**: {coverage_ratio:.0%}",
            f"**Children Evaluated**: {total_children}",
            "",
            "**Satisfied / Partially Satisfied Requirements**:"
        ]
        
        for res in child_results:
            if res.status in ("compliant", "partial"):
                # Extract title from justification if possible
                req_lines = res.justification.split('\n')
                req_title = res.requirement_id
                for line in req_lines:
                    if line.startswith("REQUIREMENT ("):
                        req_title = line.replace("REQUIREMENT (", "").rstrip("):")
                        break
                icon = "✅" if res.status == "compliant" else "⚠️"
                summary_lines.append(f"{icon} {res.requirement_id}: {req_title}")
                
        summary_lines.append("")
        summary_lines.append("**Missing / Failed Requirements**:")
        
        has_failed = False
        for res in child_results:
            if res.status == "non_compliant":
                has_failed = True
                req_lines = res.justification.split('\n')
                req_title = res.requirement_id
                for line in req_lines:
                    if line.startswith("REQUIREMENT ("):
                        req_title = line.replace("REQUIREMENT (", "").rstrip("):")
                        break
                summary_lines.append(f"❌ {res.requirement_id}: {req_title}")
                
        if not has_failed:
            summary_lines.append("None")
            
        justification = "\n".join(summary_lines)
        
        # Collect all evidence references
        all_evidence = []
        for res in child_results:
            for ev in res.evidence_references:
                if ev not in all_evidence:
                    all_evidence.append(ev)
                    
        return AssessmentResultCreate(
            requirement_id=group_id,
            status=overall_status,
            confidence_score=coverage_ratio,
            justification=justification,
            evidence_references=all_evidence[:10]  # Cap at top 10 unique evidence items
        )
