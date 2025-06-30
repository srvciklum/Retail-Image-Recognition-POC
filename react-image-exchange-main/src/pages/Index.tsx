import React, { useState } from "react";
import { ImageUpload } from "@/components/ImageUpload";
import { ImageDisplay } from "@/components/ImageDisplay";
import { toast } from "sonner";
import ProductTable from "../components/ProductTable";
import { Button } from "@/components/ui/button";
import { RefreshCcw, Upload } from "lucide-react";

const Index = () => {
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [processedImage, setProcessedImage] = useState<string | null>(null);
  const [responseText, setResponseText] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [detectedCounts, setDetectedCounts] = useState<Record<string, number>>({});
  const [emptyShelfItems, setEmptyShelfItems] = useState<string[]>([]);

  const handleImageUpload = async (file: File) => {
    setUploadedImage(URL.createObjectURL(file));
    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append("image", file);

      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

      const response = await fetch(`${apiBaseUrl}/analyze`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      const filteredEmptyItems = result.empty_shelf_items.filter(
        (item: string) => item.trim().toLowerCase() !== "unknown item"
      );

      setProcessedImage(`${apiBaseUrl}/${result.saved_image_path}`);
      setDetectedCounts(result.detected_counts);
      setEmptyShelfItems(filteredEmptyItems);
      setResponseText(result.text || "");

      toast.success("Image processed successfully!");
    } catch (error) {
      console.error("Error processing image:", error);
      toast.error("Failed to process image. Please check if your backend service is running.");
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
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <div className="text-center mb-12 space-y-4">
          <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 mb-4">
            AI-Powered Shelf Intelligence
          </h1>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Upload a store shelf image and let our AI detect products, identify empty spaces, and extract key insights —
            all in seconds.
          </p>
        </div>

        {/* Main Content */}
        <div className="space-y-8">
          {/* Upload Section */}
          {!uploadedImage ? (
            <div className="max-w-2xl mx-auto">
              <ImageUpload onImageUpload={handleImageUpload} isLoading={isLoading} />
            </div>
          ) : (
            <div className="text-center mb-8">
              <Button onClick={handleReset} variant="outline" size="lg" className="group">
                <RefreshCcw className="w-4 h-4 mr-2 group-hover:rotate-180 transition-transform duration-300" />
                Upload New Image
              </Button>
            </div>
          )}

          {/* Results Section */}
          {uploadedImage && (
            <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <ImageDisplay
                originalImage={uploadedImage}
                processedImage={processedImage}
                responseText={responseText}
                isLoading={isLoading}
              />

              <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
                <ProductTable detectedCounts={detectedCounts} emptyShelfItems={emptyShelfItems} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Index;
