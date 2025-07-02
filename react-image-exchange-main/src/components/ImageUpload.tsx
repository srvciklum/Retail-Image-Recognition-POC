import React, { useCallback, useState, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, Image as ImageIcon, FileImage, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface Planogram {
  id: string;
  name: string;
}

interface ImageUploadProps {
  onImageUpload: (file: File, planogramId?: string) => void;
  isLoading: boolean;
}

export const ImageUpload: React.FC<ImageUploadProps> = ({ onImageUpload, isLoading }) => {
  const [dragActive, setDragActive] = useState(false);
  const [planograms, setPlanograms] = useState<Planogram[]>([]);
  const [selectedPlanogramId, setSelectedPlanogramId] = useState<string>("none");
  const [error, setError] = useState<string | null>(null);

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

  useEffect(() => {
    fetchPlanograms();
  }, []);

  const fetchPlanograms = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/planograms`);
      if (response.ok) {
        const data = await response.json();
        setPlanograms(data);
      }
    } catch (error) {
      console.error("Error fetching planograms:", error);
      setError("Failed to load planograms. Please try again later.");
    }
  };

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      setError(null);
      if (acceptedFiles.length > 0 && !isLoading) {
        const file = acceptedFiles[0];
        if (file.type.startsWith("image/")) {
          if (file.size > 10 * 1024 * 1024) {
            setError("Image size should be less than 10MB");
            return;
          }
          onImageUpload(file, selectedPlanogramId === "none" ? undefined : selectedPlanogramId);
        } else {
          setError("Please upload a valid image file");
        }
      }
    },
    [onImageUpload, isLoading, selectedPlanogramId]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/*": [".jpeg", ".jpg", ".png", ".gif"],
    },
    disabled: isLoading,
    multiple: false,
    maxSize: 10 * 1024 * 1024, // 10MB
  });

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4 justify-between">
          <div className="space-y-2 flex-1">
            <Label htmlFor="planogram" className="text-base font-medium">
              Select Planogram
            </Label>
            <p className="text-sm text-muted-foreground">Choose a planogram to check shelf compliance</p>
          </div>
          <div className="sm:w-[300px]">
            <Select value={selectedPlanogramId} onValueChange={setSelectedPlanogramId}>
              <SelectTrigger id="planogram" className="w-full">
                <SelectValue placeholder="Choose a planogram" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Shelf Detection</SelectItem>
                {planograms.map((planogram) => (
                  <SelectItem key={planogram.id} value={planogram.id}>
                    {planogram.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Card
          {...getRootProps()}
          className={cn(
            "border-2 border-dashed relative cursor-pointer transition-all duration-300",
            isDragActive
              ? "border-primary bg-primary/5 scale-[1.02]"
              : "border-muted-foreground/25 hover:border-primary/50",
            isLoading && "opacity-50 cursor-not-allowed"
          )}
        >
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <input {...getInputProps()} />
            <div className="flex flex-col items-center gap-4">
              <div
                className={cn(
                  "p-6 rounded-full transition-colors duration-300",
                  isDragActive ? "bg-primary/20" : "bg-primary/10",
                  isLoading && "animate-pulse"
                )}
              >
                {isLoading ? (
                  <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Upload className="w-12 h-12 text-primary" />
                )}
              </div>
              <div className="space-y-2">
                <h3 className="font-semibold text-xl">
                  {isLoading ? "Analyzing image..." : isDragActive ? "Drop to analyze" : "Upload shelf image"}
                </h3>
                <p className="text-muted-foreground max-w-[20rem] mx-auto leading-relaxed">
                  {isLoading
                    ? "Please wait while we process your image"
                    : "Drag and drop your image here, or click to browse"}
                </p>
              </div>
            </div>
            <div className="mt-6 flex flex-col items-center gap-2">
              <div className="text-sm text-muted-foreground">Supported formats: JPEG, PNG, GIF</div>
              <div className="text-xs text-muted-foreground">Maximum file size: 10MB</div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
