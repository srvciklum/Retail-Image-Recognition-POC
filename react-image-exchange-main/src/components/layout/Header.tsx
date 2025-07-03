import React from "react";
import { Button } from "@/components/ui/button";
import { RefreshCcw, Grid } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { PlanogramManager } from "@/components/features/planogram/PlanogramManager";

interface HeaderProps {
  onReset: () => void;
  showPlanogramDialog: boolean;
  setShowPlanogramDialog: (show: boolean) => void;
}

export const Header: React.FC<HeaderProps> = ({ onReset, showPlanogramDialog, setShowPlanogramDialog }) => {
  return (
    <div className="bg-white border-b sticky top-0 z-50 shadow-sm">
      <div className="container mx-auto px-4 py-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
              AI-Powered Shelf Intelligence
            </h1>
            <p className="text-muted-foreground mt-2">Automated shelf monitoring and planogram compliance analysis</p>
          </div>
          <div className="flex items-center gap-2 justify-start">
            <Dialog open={showPlanogramDialog} onOpenChange={setShowPlanogramDialog}>
              <DialogTrigger asChild>
                <Button variant="outline" className="gap-2">
                  <Grid className="w-5 h-5 text-primary" />
                  Planogram Management
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-[95vw] w-full h-[90vh] p-0 flex flex-col">
                <DialogHeader className="px-6 py-4 border-b flex-shrink-0">
                  <DialogTitle className="flex items-center gap-2">Planogram Management</DialogTitle>
                </DialogHeader>
                <div className="flex-1 overflow-auto">
                  <div className="p-6">
                    <PlanogramManager />
                  </div>
                </div>
              </DialogContent>
            </Dialog>
            <Button variant="outline" onClick={onReset} className="gap-2">
              <RefreshCcw className="w-4 h-4" />
              Reset
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
