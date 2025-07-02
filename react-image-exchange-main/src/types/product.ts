export interface Product {
  id: string;
  name: string;
  variants: string[];
  category?: string;
  description?: string;
  image_url?: string;
}
