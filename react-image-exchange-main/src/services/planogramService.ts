import { Planogram, PlanogramCreate } from "@/types/planogram";
import { API_CONFIG } from "@/config/api";

export const planogramService = {
  async listPlanograms(): Promise<Planogram[]> {
    const response = await fetch(API_CONFIG.getFullUrl("/planograms"));
    if (!response.ok) {
      throw new Error("Failed to fetch planograms");
    }
    return response.json();
  },

  async getPlanogram(id: string): Promise<Planogram> {
    const response = await fetch(API_CONFIG.getFullUrl(`/planograms/${id}`));
    if (!response.ok) {
      throw new Error("Failed to fetch planogram");
    }
    return response.json();
  },

  async createPlanogram(planogram: PlanogramCreate): Promise<Planogram> {
    const response = await fetch(API_CONFIG.getFullUrl("/planograms"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(planogram),
    });
    if (!response.ok) {
      throw new Error("Failed to create planogram");
    }
    return response.json();
  },

  async updatePlanogram(id: string, planogram: PlanogramCreate): Promise<Planogram> {
    const response = await fetch(API_CONFIG.getFullUrl(`/planograms/${id}`), {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(planogram),
    });
    if (!response.ok) {
      throw new Error("Failed to update planogram");
    }
    return response.json();
  },

  async deletePlanogram(id: string): Promise<void> {
    const response = await fetch(API_CONFIG.getFullUrl(`/planograms/${id}`), {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error("Failed to delete planogram");
    }
  },
};
