import React, { useState } from "react";
import { Header } from "@/components/layout/Header";
import { ImageAnalysis } from "@/components/features/image-analysis/ImageAnalysis";
import { Toaster } from "@/components/ui/toaster";

const App = () => {
  const [showPlanogramDialog, setShowPlanogramDialog] = useState(false);
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

  const handleReset = () => {
    // This will be handled by the ImageAnalysis component
    window.location.reload();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-12">
      <Header
        onReset={handleReset}
        showPlanogramDialog={showPlanogramDialog}
        setShowPlanogramDialog={setShowPlanogramDialog}
      />
      <ImageAnalysis apiBaseUrl={apiBaseUrl} />
      <Toaster />
    </div>
  );
};

export default App;
