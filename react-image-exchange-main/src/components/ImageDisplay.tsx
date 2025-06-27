
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

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
  isLoading
}) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 max-w-6xl mx-auto items-start">
      {/* Original Image */}
<Card className="overflow-hidden w-full">
  <CardHeader className="pb-2">
    <CardTitle className="flex items-center gap-2 text-lg">
      Original Image
      <Badge variant="secondary">Input</Badge>
    </CardTitle>
  </CardHeader>

  <CardContent className="p-0">
    <div className="w-full flex justify-center">
      <img
        src={originalImage}
        alt="Original uploaded image"
        className="object-contain max-w-full max-h-[500px]"
      />
    </div>
  </CardContent>
</Card>

      {/* Processed Image */}
  <Card className="overflow-hidden w-full">
  <CardHeader className="pb-2">
    <CardTitle className="flex items-center gap-2 text-lg">
      Processed Image
      <Badge variant={processedImage ? "default" : "outline"}>
        {isLoading ? 'Processing...' : processedImage ? 'Output' : 'Pending'}
      </Badge>
    </CardTitle>
  </CardHeader>

  <CardContent className="p-1">
    <div className="w-full flex justify-center">
      {isLoading ? (
        <div className="space-y-4 w-full p-8">
          <Skeleton className="w-full h-48" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-3/4 mx-auto" />
            <Skeleton className="h-4 w-1/2 mx-auto" />
          </div>
        </div>
      ) : processedImage ? (
        <img
          src={processedImage}
          alt="Processed image from backend"
          className="object-contain max-w-full max-h-[500px]"
        />
      ) : (
        <div className="text-center text-muted-foreground p-8">
          <div className="w-16 h-16 mx-auto mb-4 bg-muted-foreground/10 rounded-full flex items-center justify-center">
            <div className="w-8 h-8 border-2 border-dashed border-muted-foreground/30 rounded" />
          </div>
          <p>Processed image will appear here</p>
        </div>
      )}
    </div>
  </CardContent>
</Card>


      {/* Response Text */}
      {(responseText || isLoading) && (
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Processing Results</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-4/5" />
                  <Skeleton className="h-4 w-3/5" />
                </div>
              ) : (
                <p className="text-foreground leading-relaxed whitespace-pre-wrap">
                  {responseText}
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};
