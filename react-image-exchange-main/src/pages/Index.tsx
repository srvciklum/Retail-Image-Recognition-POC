import React, { useState, useRef, useEffect } from "react";
import { ImageUpload, ImageUploadRef } from "@/components/ImageUpload";
import { ImageDisplay } from "@/components/ImageDisplay";
import { toast } from "sonner";
import ProductTable from "../components/ProductTable";
import { Button } from "@/components/ui/button";
import { RefreshCcw, Plus, Upload, Grid } from "lucide-react";
import { ComplianceResults } from "@/components/ComplianceResults";
import { Card } from "@/components/ui/card";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { PlanogramManager } from "@/components/PlanogramManager";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { planogramService } from "@/services/planogramService";
import { Planogram } from "@/types/planogram";

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

const Index = () => {
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [processedImage, setProcessedImage] = useState<string | null>(null);
  const [responseText, setResponseText] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [detectedCounts, setDetectedCounts] = useState<Record<string, number>>({});
  const [emptyShelfItems, setEmptyShelfItems] = useState<string[]>([]);
  const [complianceResult, setComplianceResult] = useState<ComplianceResult | null>(null);
  const [activeAccordion, setActiveAccordion] = useState<string>("upload");
  const [showPlanogramDialog, setShowPlanogramDialog] = useState(false);
  const [planogramData, setPlanogramData] = useState<Planogram | null>(null);

  const imageUploadRef = useRef<ImageUploadRef>(null);
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

  // Refresh planograms when dialog closes
  useEffect(() => {
    if (!showPlanogramDialog && imageUploadRef.current) {
      imageUploadRef.current.refreshPlanograms();
    }
  }, [showPlanogramDialog]);

  // Fetch planogram data when compliance results arrive
  useEffect(() => {
    const fetchPlanogramData = async () => {
      if (complianceResult && complianceResult.planogram_name) {
        try {
          const planograms = await planogramService.listPlanograms();
          const matchingPlanogram = planograms.find((p) => p.name === complianceResult.planogram_name);
          if (matchingPlanogram) {
            setPlanogramData(matchingPlanogram);
          } else {
            console.warn("Could not find planogram with name:", complianceResult.planogram_name);
            setPlanogramData(null);
          }
        } catch (error) {
          console.error("Error fetching planogram data:", error);
          toast.error("Failed to load planogram data for grid view");
          setPlanogramData(null);
        }
      } else {
        setPlanogramData(null);
      }
    };

    fetchPlanogramData();
  }, [complianceResult]);

  const handleImageUpload = async (file: File, planogramId?: string) => {
    setIsLoading(true);
    setUploadedImage(URL.createObjectURL(file));
    setProcessedImage(null);
    setResponseText("");
    setDetectedCounts({});
    setEmptyShelfItems([]);
    setComplianceResult(null);
    setPlanogramData(null);
    setActiveAccordion("");

    const formData = new FormData();
    formData.append("image", file);
    if (planogramId && planogramId !== "none") {
      formData.append("planogram_id", planogramId);
    }

    try {
      const response = await fetch(`${apiBaseUrl}/analyze`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to process image");
      }

      const data = await response.json();
      setProcessedImage(`${apiBaseUrl}/${data.saved_image_path}`);
      setDetectedCounts(data.detected_counts);
      setEmptyShelfItems(data.empty_shelf_items);
      if (data.compliance_result) {
        setComplianceResult(data.compliance_result);
      }
      toast.success("Image processed successfully");
    } catch (error) {
      console.error("Error processing image:", error);
      toast.error("Failed to process image");
      setActiveAccordion("upload");
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setUploadedImage(null);
    setProcessedImage(null);
    setResponseText("");
    setDetectedCounts({});
    setEmptyShelfItems([]);
    setComplianceResult(null);
    setPlanogramData(null);
    setActiveAccordion("upload");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-12">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-50 shadow-sm">
        <div className="container mx-auto px-4 py-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
                AI-Powered Shelf Intelligence
              </h1>
              <p className="text-muted-foreground mt-2">Analyze store shelves with advanced AI detection</p>
            </div>
            <div className="flex items-center gap-2 justify-start">
              <Dialog open={showPlanogramDialog} onOpenChange={setShowPlanogramDialog}>
                <DialogTrigger asChild>
                  <Button variant="outline" className="gap-2">
                    <Grid className="w-5 h-5 text-primary" />
                    Planogram Management
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-[95vw] w-full h-[90vh] p-0 flex flex-col">
                  <DialogHeader className="px-6 py-4 border-b flex-shrink-0">
                    <DialogTitle className="flex items-center gap-2">Planogram Management</DialogTitle>
                  </DialogHeader>
                  <div className="flex-1 overflow-auto">
                    <div className="p-6">
                      <PlanogramManager />
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
              <Button variant="outline" onClick={handleReset} className="gap-2">
                <RefreshCcw className="w-4 h-4" />
                Reset
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-8">
          <Accordion
            type="single"
            collapsible
            value={activeAccordion}
            onValueChange={setActiveAccordion}
            className="space-y-4"
          >
            <AccordionItem value="upload" className="border rounded-lg overflow-hidden">
              <AccordionTrigger className="px-6 py-4 hover:no-underline">
                <div className="flex items-center gap-2">
                  <Upload className="w-4 h-4" />
                  <span className="font-semibold">Upload & Configure</span>
                  {uploadedImage && <span className="text-sm text-muted-foreground">(Image uploaded)</span>}
                </div>
              </AccordionTrigger>
              <AccordionContent className="border-t">
                <div className="p-6">
                  <Card className="border-2 border-dashed hover:border-blue-500/50 transition-colors">
                    <div className="p-6">
                      <ImageUpload ref={imageUploadRef} onImageUpload={handleImageUpload} isLoading={isLoading} />
                    </div>
                  </Card>
                </div>
              </AccordionContent>
            </AccordionItem>

            {(uploadedImage || processedImage) && (
              <>
                <div className="border rounded-lg overflow-hidden bg-white p-6">
                  <ImageDisplay
                    originalImage={uploadedImage!}
                    processedImage={processedImage}
                    responseText={responseText}
                    isLoading={isLoading}
                    complianceResult={complianceResult}
                    planogramData={planogramData}
                  />
                </div>

                {complianceResult && (
                  <AccordionItem value="compliance" className="border rounded-lg overflow-hidden">
                    <AccordionTrigger className="px-6 py-4 hover:no-underline">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold">Planogram Compliance</span>
                        <span className="text-sm text-muted-foreground">
                          ({Math.round(complianceResult.compliance_score)}% compliance)
                        </span>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent className="border-t">
                      <div className="p-6">
                        <ComplianceResults results={complianceResult} />
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                )}

                {Object.keys(detectedCounts).length > 0 && (
                  <AccordionItem value="detection" className="border rounded-lg overflow-hidden">
                    <AccordionTrigger className="px-6 py-4 hover:no-underline">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold">Detection Results</span>
                        <span className="text-sm text-muted-foreground">
                          ({Object.keys(detectedCounts).length} products detected)
                        </span>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent className="border-t">
                      <div className="p-6">
                        <ProductTable detectedCounts={detectedCounts} emptyShelfItems={emptyShelfItems} />
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                )}
              </>
            )}
          </Accordion>
        </div>
      </div>
    </div>
  );
};

export default Index;
