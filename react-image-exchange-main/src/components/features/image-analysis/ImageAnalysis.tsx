import React, { useState, useRef, useEffect } from "react";
import { ImageUpload, ImageUploadRef } from "./ImageUpload";
import { ImageDisplay } from "./ImageDisplay";
import { ComplianceResults } from "./ComplianceResults";
import { ProductTable } from "./ProductTable";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Card } from "@/components/ui/card";
import { Upload } from "lucide-react";
import { toast } from "sonner";
import { planogramService } from "@/services/planogramService";
import { Planogram } from "@/types/planogram";
import { ComplianceResult } from "@/types/planogram";
import { API_CONFIG } from "@/config/api";

interface ImageAnalysisProps {
  apiBaseUrl: string;
}

export const ImageAnalysis: React.FC<ImageAnalysisProps> = ({ apiBaseUrl }) => {
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [processedImage, setProcessedImage] = useState<string | null>(null);
  const [responseText, setResponseText] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [detectedCounts, setDetectedCounts] = useState<Record<string, number>>({});
  const [emptyShelfItems, setEmptyShelfItems] = useState<string[]>([]);
  const [complianceResult, setComplianceResult] = useState<ComplianceResult | null>(null);
  const [activeAccordion, setActiveAccordion] = useState<string[]>(["upload"]);
  const [planogramData, setPlanogramData] = useState<Planogram | null>(null);

  const imageUploadRef = useRef<ImageUploadRef>(null);

  // Refresh planograms when component mounts and when dialog closes
  useEffect(() => {
    const refreshPlanograms = () => {
      if (imageUploadRef.current) {
        imageUploadRef.current.refreshPlanograms();
      }
    };

    // Listen for dialog close events
    const handleDialogClose = () => {
      refreshPlanograms();
    };

    window.addEventListener("planogram-dialog-close", handleDialogClose);
    refreshPlanograms(); // Initial load

    return () => {
      window.removeEventListener("planogram-dialog-close", handleDialogClose);
    };
  }, []);

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
    setActiveAccordion(["upload"]);

    const formData = new FormData();
    formData.append("image", file);
    if (planogramId && planogramId !== "none") {
      formData.append("planogram_id", planogramId);
    }

    try {
      const response = await fetch(API_CONFIG.getFullUrl("/analyze"), {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to process image");
      }

      const data = await response.json();
      setProcessedImage(`${API_CONFIG.baseUrl}/api/v1/images/${data.saved_image_path.split("/").pop()}`);
      setDetectedCounts(data.detected_counts);
      setEmptyShelfItems(data.empty_shelf_items);

      // Set active accordion items based on available results
      const activeItems = [];
      if (data.compliance_result) {
        setComplianceResult(data.compliance_result);
        activeItems.push("compliance");
      }
      if (data.detected_counts && Object.keys(data.detected_counts).length > 0) {
        activeItems.push("detection");
      }
      setActiveAccordion(activeItems);

      toast.success("Image processed successfully");
    } catch (error) {
      console.error("Error processing image:", error);
      toast.error("Failed to process image");
      setActiveAccordion(["upload"]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="space-y-8">
        <Accordion type="multiple" value={activeAccordion} onValueChange={setActiveAccordion} className="space-y-4">
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
  );
};
