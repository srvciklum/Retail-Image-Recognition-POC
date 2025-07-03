import React from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { CheckCircle2, XCircle, AlertTriangle, Package2, PackageX, PackageSearch } from "lucide-react";
import { Progress } from "@/components/ui/progress";

interface ComplianceIssue {
  row: number;
  column: number;
  issue_type: string;
  expected: string;
  found: string;
  severity: "high" | "medium" | "low";
}

interface ComplianceResults {
  is_compliant: boolean;
  compliance_score: number;
  issues: ComplianceIssue[];
  correct_placements: number;
  total_positions: number;
  planogram_name: string;
}

interface Props {
  results: ComplianceResults;
}

const getIssueIcon = (issue_type: string) => {
  switch (issue_type) {
    case "wrong_product":
      return <Package2 className="h-5 w-5 text-red-500" />;
    case "out_of_stock":
      return <PackageX className="h-5 w-5 text-red-500" />;
    case "undetected":
      return <PackageSearch className="h-5 w-5 text-orange-500" />;
    default:
      return <PackageSearch className="h-5 w-5 text-yellow-500" />;
  }
};

const getSeverityColor = (issue: ComplianceIssue) => {
  // Special color for undetected issues
  if (issue.issue_type === "undetected") {
    return "border-orange-200 bg-orange-50";
  }

  // All other issues are high severity (red)
  return "border-red-200 bg-red-50";
};

const getIssueTitle = (issue: ComplianceIssue) => {
  switch (issue.issue_type) {
    case "wrong_product":
      return "Incorrect Product Placement";
    case "out_of_stock":
      return "Empty Shelf Space";
    case "undetected":
      return "Undetected Product Area";
    default:
      return "Compliance Issue";
  }
};

const convertTo1BasedShelf = (text: string) => {
  // Convert "Shelf 0" to "Shelf 1", "Shelf 1" to "Shelf 2", etc.
  return text.replace(/Shelf (\d+)/, (match, shelfNumber) => {
    const oneBasedShelf = parseInt(shelfNumber) + 1;
    return `Shelf ${oneBasedShelf}`;
  });
};

export const ComplianceResults: React.FC<Props> = ({ results }) => {
  const compliancePercentage = Math.round(results.compliance_score);

  // Sort issues by type for better organization
  const sortedIssues = [...results.issues].sort((a, b) => {
    const typeOrder: { [key: string]: number } = { wrong_product: 0, out_of_stock: 1, undetected: 2 };
    return (typeOrder[a.issue_type] || 999) - (typeOrder[b.issue_type] || 999);
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Planogram Compliance</h2>
          <p className="text-muted-foreground">
            {results.correct_placements} of {results.total_positions} positions correct
          </p>
          <p className="text-sm text-muted-foreground mt-1">
            Using planogram: <span className="font-medium text-foreground">{results.planogram_name}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          {results.is_compliant ? (
            <CheckCircle2 className="h-6 w-6 text-green-500" />
          ) : (
            <XCircle className="h-6 w-6 text-red-500" />
          )}
          <span className="text-2xl font-bold">{compliancePercentage}%</span>
        </div>
      </div>

      <Progress value={compliancePercentage} className="h-2" />

      {sortedIssues.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold mb-4">Compliance Issues</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {sortedIssues.map((issue, index) => (
              <Alert key={index} className={`flex items-start gap-3 h-full ${getSeverityColor(issue)}`}>
                <div className="mt-0.5">{getIssueIcon(issue.issue_type)}</div>
                <div className="flex-1">
                  <AlertTitle className="text-base font-semibold">{getIssueTitle(issue)}</AlertTitle>
                  <AlertDescription className="mt-2 space-y-2">
                    <div className="text-sm">
                      <span className="font-medium">Location:</span> {convertTo1BasedShelf(issue.expected)}
                    </div>
                    <div className="text-sm">
                      <span className="font-medium">Issue:</span> {issue.found}
                    </div>
                  </AlertDescription>
                </div>
              </Alert>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
