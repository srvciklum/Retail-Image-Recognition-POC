from pydantic import BaseModel
from typing import List, Literal

class ComplianceIssue(BaseModel):
    row: int
    column: int
    issue_type: str
    expected: str
    found: str
    severity: Literal["high", "medium", "low"]

class ComplianceResult(BaseModel):
    is_compliant: bool
    compliance_score: float
    issues: List[ComplianceIssue]
    correct_placements: int
    total_positions: int
    planogram_name: str 