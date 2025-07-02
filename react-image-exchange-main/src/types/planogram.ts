export interface PlanogramSection {
  column: number;
  expected_product: string;
  allowed_variants: string[];
  min_quantity: number;
  max_quantity: number;
}

export interface PlanogramShelf {
  row: number;
  sections: PlanogramSection[];
}

export interface PlanogramCreate {
  name: string;
  shelves: PlanogramShelf[];
}

export interface Planogram extends PlanogramCreate {
  id: string;
  created_at?: string;
  updated_at?: string;
}

export interface ComplianceIssue {
  row: number;
  column: number;
  issue_type: string;
  expected: string;
  found: string;
  severity: "high" | "medium" | "low";
}

export interface ComplianceResult {
  is_compliant: boolean;
  compliance_score: number;
  issues: ComplianceIssue[];
  correct_placements: number;
  total_positions: number;
}
