import { Planogram, PlanogramCreate } from "@/types/planogram";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export const planogramService = {
  async listPlanograms(): Promise<Planogram[]> {
    const response = await fetch(`${API_BASE_URL}/planograms`);
    if (!response.ok) {
      throw new Error("Failed to fetch planograms");
    }
    return response.json();
  },

  async getPlanogram(id: string): Promise<Planogram> {
    const response = await fetch(`${API_BASE_URL}/planograms/${id}`);
    if (!response.ok) {
      throw new Error("Failed to fetch planogram");
    }
    return response.json();
  },

  async createPlanogram(planogram: PlanogramCreate): Promise<Planogram> {
    const response = await fetch(`${API_BASE_URL}/planograms`, {
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
    const response = await fetch(`${API_BASE_URL}/planograms/${id}`, {
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
    const response = await fetch(`${API_BASE_URL}/planograms/${id}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error("Failed to delete planogram");
    }
  },
};
