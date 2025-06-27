import React, { useState } from 'react';
import { ImageUpload } from '@/components/ImageUpload';
import { ImageDisplay } from '@/components/ImageDisplay';
import Sidebar from "@/components/sidebar"; 
import { toast } from 'sonner';
import ProductTable from '../components/ProductTable';

const Index = () => {
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [processedImage, setProcessedImage] = useState<string | null>(null);
  const [responseText, setResponseText] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [detectedCounts, setDetectedCounts] = useState<Record<string, number>>({});
  const [emptyShelfItems, setEmptyShelfItems] = useState<string[]>([]);

  const handleImageUpload = async (file: File) => {
    setUploadedImage(URL.createObjectURL(file));
    setIsLoading(true);
    
    try {
      const formData = new FormData();
      formData.append('image', file);
      
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

      const response = await fetch(`${apiBaseUrl}/analyze`, {
        method: 'POST',
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
      setResponseText(result.text || '');
      
      toast.success('Image processed successfully!');
    } catch (error) {
      console.error('Error processing image:', error);
      toast.error('Failed to process image. Please check if your backend service is running.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setUploadedImage(null);
    setProcessedImage(null);
    setResponseText('');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex">
      {/* Sidebar */}
      {/* Main Content */}
      <div className="flex-1 px-8 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-foreground mb-4">
            AI-Powered Shelf Intelligence
          </h1>
          <p className="text-muted-foreground text-lg max-w-1xl mx-auto">
            Upload a store shelf image and let our AI detect products, identify empty spaces, and extract key insights — all in seconds.
          </p>
        </div>

        {/* Upload Section */}
        {!uploadedImage && (
          <div className="max-w-2xl mx-auto mb-4">
            <ImageUpload onImageUpload={handleImageUpload} isLoading={isLoading} />
          </div>
        )}

        {/* Results Section */}
        {uploadedImage && (
          <div className="space-y-8">
            <div className="text-center">
              <button
                onClick={handleReset}
                className="inline-flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-md transition-colors duration-300"
              >
                Upload New Image
              </button>
            </div>

            <ImageDisplay
              originalImage={uploadedImage}
              processedImage={processedImage}
              responseText={responseText}
              isLoading={isLoading}
            />

            <div className="bg-gray-50 p-6 rounded-lg shadow">
              <ProductTable
                detectedCounts={detectedCounts}
                emptyShelfItems={emptyShelfItems}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Index;