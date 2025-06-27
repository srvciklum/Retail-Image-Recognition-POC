
import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Image as ImageIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

interface ImageUploadProps {
  onImageUpload: (file: File) => void;
  isLoading: boolean;
}

export const ImageUpload: React.FC<ImageUploadProps> = ({ onImageUpload, isLoading }) => {
  const [dragActive, setDragActive] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0 && !isLoading) {
      const file = acceptedFiles[0];
      if (file.type.startsWith('image/')) {
        onImageUpload(file);
      }
    }
  }, [onImageUpload, isLoading]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.gif', '.bmp', '.webp']
    },
    multiple: false,
    disabled: isLoading
  });

  return (
    <Card className="border-2 border-dashed border-border hover:border-primary/50 transition-colors">
      <CardContent className="p-8">
        <div
          {...getRootProps()}
          className={`text-center cursor-pointer transition-all duration-200 ${
            isDragActive ? 'scale-105' : ''
          } ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <input {...getInputProps()} />
          
          <div className="mb-6">
            {isLoading ? (
              <div className="w-16 h-16 mx-auto mb-4 border-4 border-primary border-t-transparent rounded-full animate-spin" />
            ) : (
              <div className="w-16 h-16 mx-auto mb-4 bg-primary/10 rounded-full flex items-center justify-center">
                {isDragActive ? (
                  <ImageIcon className="w-8 h-8 text-primary" />
                ) : (
                  <Upload className="w-8 h-8 text-primary" />
                )}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <h3 className="text-xl font-semibold text-foreground">
              {isLoading ? 'Processing...' : 'Upload your image'}
            </h3>
            <p className="text-muted-foreground">
              {isLoading 
                ? 'Please wait while we process your image'
                : isDragActive 
                  ? 'Drop your image here'
                  : 'Drag and drop an image here, or click to browse'
              }
            </p>
          </div>

          {!isLoading && (
            <Button className="mt-6" size="lg">
              <Upload className="w-4 h-4 mr-2" />
              Browse Files
            </Button>
          )}

          <p className="text-sm text-muted-foreground mt-4">
            Supports: JPEG
          </p>
        </div>
      </CardContent>
    </Card>
  );
};
