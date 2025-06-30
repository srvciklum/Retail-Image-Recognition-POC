import React, { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, Image as ImageIcon, FileImage } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface ImageUploadProps {
  onImageUpload: (file: File) => void;
  isLoading: boolean;
}

export const ImageUpload: React.FC<ImageUploadProps> = ({ onImageUpload, isLoading }) => {
  const [dragActive, setDragActive] = useState(false);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0 && !isLoading) {
        const file = acceptedFiles[0];
        if (file.type.startsWith("image/")) {
          onImageUpload(file);
        }
      }
    },
    [onImageUpload, isLoading]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/*": [".jpeg", ".jpg", ".png", ".gif", ".bmp", ".webp"],
    },
    multiple: false,
    disabled: isLoading,
  });

  return (
    <Card
      className={cn(
        "border-2 border-dashed transition-all duration-300",
        isDragActive ? "border-primary scale-[1.02] bg-primary/5" : "border-border hover:border-primary/50",
        isLoading && "opacity-50 cursor-not-allowed"
      )}
    >
      <CardContent className="p-8">
        <div {...getRootProps()} className="text-center cursor-pointer">
          <input {...getInputProps()} />

          <div className="mb-6">
            {isLoading ? (
              <div className="relative w-20 h-20 mx-auto">
                <div className="absolute inset-0 border-4 border-primary/30 rounded-full animate-ping" />
                <div className="absolute inset-0 border-4 border-primary border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
              <div
                className={cn(
                  "w-20 h-20 mx-auto rounded-full flex items-center justify-center transition-all duration-300",
                  isDragActive ? "bg-primary/20 scale-110" : "bg-primary/10"
                )}
              >
                {isDragActive ? (
                  <FileImage className="w-10 h-10 text-primary animate-bounce" />
                ) : (
                  <ImageIcon className="w-10 h-10 text-primary" />
                )}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <h3
              className={cn(
                "text-2xl font-semibold transition-colors",
                isDragActive ? "text-primary" : "text-foreground"
              )}
            >
              {isLoading ? "Processing..." : isDragActive ? "Drop your image here" : "Upload your image"}
            </h3>
            <p className="text-muted-foreground text-sm max-w-sm mx-auto">
              {isLoading
                ? "Please wait while we analyze your image"
                : "Drag and drop your shelf image here, or click to browse"}
            </p>
          </div>

          {!isLoading && (
            <Button className={cn("mt-6 transition-all duration-300", isDragActive && "scale-105")} size="lg">
              <Upload className="w-4 h-4 mr-2" />
              Select Image
            </Button>
          )}

          <div className="flex items-center justify-center gap-2 mt-6 text-xs text-muted-foreground">
            <FileImage className="w-4 h-4" />
            <span>Supports: JPEG, PNG, GIF</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
