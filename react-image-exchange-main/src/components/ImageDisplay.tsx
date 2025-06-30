import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Image as ImageIcon, Loader2 } from "lucide-react";

interface ImageDisplayProps {
  originalImage: string;
  processedImage: string | null;
  responseText: string;
  isLoading: boolean;
}

export const ImageDisplay: React.FC<ImageDisplayProps> = ({
  originalImage,
  processedImage,
  responseText,
  isLoading,
}) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-[1400px] mx-auto">
      {/* Original Image */}
      <Card className="overflow-hidden group hover:shadow-lg transition-all duration-300">
        <CardHeader className="pb-3 border-b">
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ImageIcon className="w-5 h-5 text-blue-500" />
              Original Image
            </div>
            <Badge variant="secondary" className="capitalize">
              Input
            </Badge>
          </CardTitle>
        </CardHeader>

        <CardContent className="p-0 relative min-h-[500px] lg:min-h-[600px]">
          <img
            src={originalImage}
            alt="Original uploaded image"
            className="object-contain w-full h-full absolute inset-0 p-2"
          />
        </CardContent>
      </Card>

      {/* Processed Image */}
      <Card className={`overflow-hidden group transition-all duration-300 ${processedImage ? "hover:shadow-lg" : ""}`}>
        <CardHeader className="pb-3 border-b">
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ImageIcon className="w-5 h-5 text-indigo-500" />
              Processed Image
            </div>
            <Badge
              variant={processedImage ? "default" : "outline"}
              className={`capitalize ${isLoading ? "animate-pulse" : ""}`}
            >
              {isLoading ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Processing
                </div>
              ) : processedImage ? (
                "Output"
              ) : (
                "Pending"
              )}
            </Badge>
          </CardTitle>
        </CardHeader>

        <CardContent className="p-0 relative min-h-[500px] lg:min-h-[600px]">
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-50/50 backdrop-blur-sm">
              <div className="space-y-4 text-center">
                <Loader2 className="w-8 h-8 animate-spin mx-auto text-blue-500" />
                <p className="text-sm text-muted-foreground">Processing your image...</p>
              </div>
            </div>
          ) : processedImage ? (
            <img
              src={processedImage}
              alt="Processed image with detections"
              className="object-contain w-full h-full absolute inset-0 p-2"
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center space-y-4 text-muted-foreground">
                <div className="w-16 h-16 mx-auto rounded-full bg-slate-100 flex items-center justify-center">
                  <ImageIcon className="w-8 h-8" />
                </div>
                <p>Processed image will appear here</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Response Text */}
      {(responseText || isLoading) && (
        <div className="lg:col-span-2">
          <Card>
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
