import { Product } from "@/types/product";
import { API_CONFIG } from "@/config/api";

export const productService = {
  async listProducts(): Promise<Product[]> {
    const response = await fetch(API_CONFIG.getFullUrl("/products"));
    if (!response.ok) {
      throw new Error("Failed to fetch products");
    }
    return response.json();
  },

  async getProduct(id: string): Promise<Product> {
    const response = await fetch(API_CONFIG.getFullUrl(`/products/${id}`));
    if (!response.ok) {
      throw new Error("Failed to fetch product");
    }
    return response.json();
  },

  async createProduct(product: Omit<Product, "id">): Promise<Product> {
    const response = await fetch(API_CONFIG.getFullUrl("/products"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(product),
    });
    if (!response.ok) {
      throw new Error("Failed to create product");
    }
    return response.json();
  },

  async updateProduct(product: Product): Promise<Product> {
    const response = await fetch(API_CONFIG.getFullUrl(`/products/${product.id}`), {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(product),
    });
    if (!response.ok) {
      throw new Error("Failed to update product");
    }
    return response.json();
  },

  async deleteProduct(id: string): Promise<void> {
    const response = await fetch(API_CONFIG.getFullUrl(`/products/${id}`), {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error("Failed to delete product");
    }
  },

  async searchProducts(query: string): Promise<Product[]> {
    const response = await fetch(API_CONFIG.getFullUrl(`/products/search/${encodeURIComponent(query)}`));
    if (!response.ok) {
      throw new Error("Failed to search products");
    }
    return response.json();
  },
};
