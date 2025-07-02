import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Image as ImageIcon, Loader2, ZoomIn, ZoomOut } from "lucide-react";
import { Button } from "./ui/button";

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
  const [isZoomed, setIsZoomed] = useState(false);

  const toggleZoom = () => setIsZoomed(!isZoomed);

  const ImageCard = ({ image, title, badge, isPending = false }) => (
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
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 w-full">
      <ImageCard image={originalImage} title="Original Image" badge="Input" />

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

      {/* Response Text */}
      {(responseText || isLoading) && (
        <div className="xl:col-span-2">
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
