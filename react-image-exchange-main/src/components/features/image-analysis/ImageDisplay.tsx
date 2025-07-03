import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Image as ImageIcon, Loader2, ZoomIn, ZoomOut, Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Planogram } from "@/types/planogram";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface ComplianceResult {
  is_compliant: boolean;
  compliance_score: number;
  issues: Array<{
    row: number;
    column: number;
    issue_type: string;
    expected: string;
    found: string;
    severity: "high" | "medium" | "low";
  }>;
  correct_placements: number;
  total_positions: number;
  planogram_name: string;
}

interface GridCell {
  status: GridCellStatus;
  expected?: string;
  found?: string;
  issueType?: string;
}

type GridCellStatus = "compliant" | "wrong_product" | "undetected" | "no_product_expected";

interface ImageDisplayProps {
  originalImage: string;
  processedImage: string | null;
  responseText: string;
  isLoading: boolean;
  complianceResult?: ComplianceResult | null;
  planogramData?: Planogram | null;
}

export const ImageDisplay: React.FC<ImageDisplayProps> = ({
  originalImage,
  processedImage,
  responseText,
  isLoading,
  complianceResult,
  planogramData,
}) => {
  const [isZoomed, setIsZoomed] = useState(false);
  const [showGridOverlay, setShowGridOverlay] = useState(true);

  const toggleZoom = () => setIsZoomed(!isZoomed);
  const toggleGridOverlay = () => setShowGridOverlay(!showGridOverlay);

  // Grid overlay logic (copied from ComplianceGridOverlay component)
  const calculateGridDimensions = (planogram: Planogram): { rows: number; cols: number } => {
    if (!planogram.shelves || planogram.shelves.length === 0) {
      return { rows: 1, cols: 1 };
    }

    const maxRow = Math.max(...planogram.shelves.map((shelf) => shelf.row));
    const maxCol = Math.max(...planogram.shelves.flatMap((shelf) => shelf.sections.map((section) => section.column)));

    return { rows: maxRow + 1, cols: maxCol + 1 };
  };

  const createGridStatusMap = (planogram: Planogram, complianceResult: ComplianceResult): GridCell[][] => {
    const { rows, cols } = calculateGridDimensions(planogram);

    // Debug logging
    console.log("=== COMPLIANCE DEBUG ===");
    console.log("Grid dimensions:", { rows, cols });
    console.log("Compliance score:", complianceResult.compliance_score);
    console.log("Total issues:", complianceResult.issues.length);
    console.log("Issues:", complianceResult.issues);

    // Log planogram expectations
    console.log("\n=== PLANOGRAM EXPECTATIONS ===");
    planogram.shelves.forEach((shelf) => {
      shelf.sections.forEach((section) => {
        console.log(`Expected at [${shelf.row}][${section.column}]: ${section.expected_product}`);
      });
    });

    const grid: GridCell[][] = Array.from({ length: rows }, () =>
      Array.from({ length: cols }, () => ({ status: "no_product_expected" as GridCellStatus }))
    );

    // Mark all positions that have expected products as compliant by default
    planogram.shelves.forEach((shelf) => {
      shelf.sections.forEach((section) => {
        if (section.expected_product) {
          console.log(
            `Setting position [${shelf.row}][${section.column}] to compliant for product: ${section.expected_product}`
          );
          grid[shelf.row][section.column] = {
            status: "compliant",
            expected: section.expected_product,
          };
        }
      });
    });

    // Apply compliance issues to mark problematic cells (now individual position issues)
    complianceResult.issues.forEach((issue, index) => {
      console.log(`Processing issue ${index + 1}:`, issue);
      console.log(
        `Issue details: type=${issue.issue_type}, expected="${issue.expected}", found="${issue.found}", row=${issue.row}, col=${issue.column}`
      );

      // Handle individual position issues
      const targetRow = Math.floor(issue.row);
      const targetCol = Math.floor(issue.column);

      // Validate coordinates
      if (targetRow < 0 || targetCol < 0 || targetRow >= rows || targetCol >= cols) {
        console.warn(
          `Issue ${index + 1} has invalid coordinates: [${issue.row}][${
            issue.column
          }] for grid size [${rows}][${cols}], skipping...`
        );
        return; // Skip this issue
      }

      // Apply issue to specific position
      let status: GridCellStatus = "wrong_product";

      if (issue.issue_type === "undetected") {
        status = "undetected";
      } else if (issue.issue_type === "wrong_product" || issue.issue_type === "out_of_stock") {
        status = "wrong_product";
      }

      console.log(`Updating cell [${targetRow}][${targetCol}] from ${grid[targetRow][targetCol].status} to ${status}`);

      // Extract expected product from the expected field (remove "Shelf X: " prefix if present)
      let expectedProduct = issue.expected;
      if (expectedProduct.includes(": ")) {
        expectedProduct = expectedProduct.split(": ")[1];
      }

      grid[targetRow][targetCol] = {
        status,
        expected: expectedProduct,
        found: issue.found,
        issueType: issue.issue_type,
      };
    });

    // Debug: Print grid status summary
    const statusCounts = {
      compliant: 0,
      wrong_product: 0,
      undetected: 0,
      no_product_expected: 0,
    };
    grid.forEach((row) => {
      row.forEach((cell) => {
        statusCounts[cell.status]++;
      });
    });
    console.log("Grid status summary:", statusCounts);
    console.log("=========================");

    return grid;
  };

  const getCellColorClass = (status: GridCellStatus): string => {
    switch (status) {
      case "compliant":
        return "bg-green-400/30 border-green-500/50";
      case "wrong_product":
        return "bg-red-400/30 border-red-500/50";
      case "undetected":
        return "bg-amber-400/30 border-amber-500/50";
      case "no_product_expected":
        return "bg-slate-200/30 border-slate-300/40";
      default:
        return "bg-slate-200/30 border-slate-300/40";
    }
  };

  const getStatusLabel = (cell: GridCell): { title: string; description: string } => {
    switch (cell.status) {
      case "compliant":
        return {
          title: "✓ Compliant",
          description: `Correct product: ${cell.expected}`,
        };
      case "wrong_product":
        return {
          title: "✗ Wrong Product",
          description: `Expected: ${cell.expected}\nFound: ${cell.found?.replace(/Found |where .* should be/, "")}`,
        };
      case "undetected":
        return {
          title: "⚠ Undetected",
          description: `Missing product: ${cell.expected}\n${cell.found}`,
        };
      case "no_product_expected":
        return {
          title: "Empty Section",
          description: "No product expected in this section",
        };
      default:
        return {
          title: "Unknown Status",
          description: "Status information not available",
        };
    }
  };

  // Check if we can show compliance overlay
  const canShowCompliance = complianceResult && planogramData;
  const gridDimensions = canShowCompliance ? calculateGridDimensions(planogramData) : null;
  const gridStatusMap = canShowCompliance ? createGridStatusMap(planogramData, complianceResult) : null;

  const ImageCard = ({ image, title, badge, isPending = false, isOriginal = false }) => (
    <Card className={`overflow-hidden group transition-all duration-300 ${image ? "hover:shadow-lg" : ""} h-full`}>
      <CardHeader className="pb-3 border-b bg-white sticky top-0 z-10">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ImageIcon className="w-5 h-5 text-blue-500" />
            {title}
          </div>
          <div className="flex items-center gap-2">
            {image && (
              <Button
                variant="ghost"
                size="sm"
                className="p-1"
                onClick={toggleZoom}
                title={isZoomed ? "Zoom Out" : "Zoom In"}
              >
                {isZoomed ? <ZoomOut className="w-4 h-4" /> : <ZoomIn className="w-4 h-4" />}
              </Button>
            )}
            {isOriginal && canShowCompliance && (
              <Button
                variant="ghost"
                size="sm"
                className="p-1"
                onClick={toggleGridOverlay}
                title={showGridOverlay ? "Hide Compliance Grid" : "Show Compliance Grid"}
              >
                {showGridOverlay ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </Button>
            )}
            <Badge
              variant={image ? "default" : "outline"}
              className={`capitalize ${isLoading && isPending ? "animate-pulse" : ""}`}
            >
              {badge}
            </Badge>
          </div>
        </CardTitle>
      </CardHeader>

      <CardContent className={`p-0 relative ${isZoomed ? "min-h-[80vh]" : "min-h-[400px] lg:min-h-[500px]"}`}>
        {image ? (
          <div className="absolute inset-0 overflow-auto">
            <div className="relative w-full h-full">
              <img
                src={image}
                alt={`${title} image`}
                className={`w-full h-full ${
                  isZoomed ? "object-contain" : "object-cover"
                } transition-all duration-300 hover:scale-[1.02]`}
                style={{
                  minHeight: isZoomed ? "80vh" : "400px",
                  objectFit: "contain",
                  padding: "1rem",
                }}
              />

              {/* Compliance Grid Overlay */}
              {isOriginal && canShowCompliance && showGridOverlay && gridDimensions && gridStatusMap && (
                <div
                  className="absolute inset-0 grid gap-0.5 p-4"
                  style={{
                    gridTemplateRows: `repeat(${gridDimensions.rows}, 1fr)`,
                    gridTemplateColumns: `repeat(${gridDimensions.cols}, 1fr)`,
                  }}
                >
                  {gridStatusMap.map((row, rowIndex) =>
                    row.map((cell, colIndex) => {
                      const statusInfo = getStatusLabel(cell);
                      return (
                        <TooltipProvider key={`${rowIndex}-${colIndex}`}>
                          <Tooltip delayDuration={0}>
                            <TooltipTrigger asChild>
                              <div
                                className={`
                                  border-2 rounded-sm transition-all duration-200 hover:scale-105
                                  ${getCellColorClass(cell.status)}
                                  flex items-center justify-center
                                `}
                                style={{
                                  gridRow: rowIndex + 1,
                                  gridColumn: colIndex + 1,
                                }}
                              >
                                <div className="w-full h-full flex items-center justify-center text-slate-700 font-bold relative">
                                  {cell.status === "compliant" && <span className="text-2xl text-green-600">✓</span>}
                                  {cell.status === "wrong_product" && <span className="text-2xl text-red-600">✗</span>}
                                  {cell.status === "undetected" && <span className="text-2xl text-amber-600">⚠</span>}
                                </div>
                              </div>
                            </TooltipTrigger>
                            <TooltipContent
                              side="right"
                              className={`max-w-[300px] p-3 shadow-lg rounded-lg border ${
                                cell.status === "compliant"
                                  ? "bg-green-50 border-green-200"
                                  : cell.status === "wrong_product"
                                  ? "bg-red-50 border-red-200"
                                  : cell.status === "undetected"
                                  ? "bg-amber-50 border-amber-200"
                                  : "bg-white border-gray-200"
                              }`}
                            >
                              <div className="space-y-1">
                                <p
                                  className={`font-semibold ${
                                    cell.status === "compliant"
                                      ? "text-green-700"
                                      : cell.status === "wrong_product"
                                      ? "text-red-700"
                                      : cell.status === "undetected"
                                      ? "text-amber-700"
                                      : "text-gray-700"
                                  }`}
                                >
                                  {statusInfo.title}
                                </p>
                                <p
                                  className={`text-sm ${
                                    cell.status === "compliant"
                                      ? "text-green-600"
                                      : cell.status === "wrong_product"
                                      ? "text-red-600"
                                      : cell.status === "undetected"
                                      ? "text-amber-600"
                                      : "text-gray-600"
                                  }`}
                                >
                                  {statusInfo.description}
                                </p>
                              </div>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      );
                    })
                  )}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-50">
            <div className="text-center space-y-4 text-muted-foreground p-6">
              <div className="w-16 h-16 mx-auto rounded-full bg-slate-100 flex items-center justify-center">
                <ImageIcon className="w-8 h-8" />
              </div>
              <p>Image will appear here</p>
            </div>
          </div>
        )}

        {isLoading && isPending && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-50/50 backdrop-blur-sm">
            <div className="space-y-4 text-center">
              <Loader2 className="w-8 h-8 animate-spin mx-auto text-blue-500" />
              <p className="text-sm text-muted-foreground">Processing your image...</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 w-full">
        <ImageCard
          image={originalImage}
          title={canShowCompliance ? "Image with Planogram Overlay" : "Original Image"}
          badge="Input"
          isOriginal={true}
        />

        <ImageCard
          image={processedImage}
          title="Processed Image"
          badge={
            isLoading ? (
              <div className="flex items-center gap-2">
                <Loader2 className="w-3 h-3 animate-spin" />
                Processing
              </div>
            ) : processedImage ? (
              "Output"
            ) : (
              "Pending"
            )
          }
          isPending={true}
        />
      </div>

      {/* Compliance Legend */}
      {canShowCompliance && showGridOverlay && (
        <div className="bg-white rounded-lg p-4 border">
          <h4 className="font-medium mb-2 text-sm">Compliance Grid Legend:</h4>
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-green-500/60 border border-green-600 rounded"></div>
              <span>Compliant</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-red-500/60 border border-red-600 rounded"></div>
              <span>Wrong Product</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-orange-500/60 border border-orange-600 rounded"></div>
              <span>Undetected</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-gray-300/40 border border-gray-400 rounded"></div>
              <span>No Product Expected</span>
            </div>
          </div>
        </div>
      )}

      {/* Response Text */}
      {(responseText || isLoading) && (
        <div>
          <Card className="bg-white/50 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="text-lg">Analysis Results</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-4/5" />
                  <Skeleton className="h-4 w-3/5" />
                </div>
              ) : (
                <p className="text-foreground leading-relaxed whitespace-pre-wrap">{responseText}</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};
