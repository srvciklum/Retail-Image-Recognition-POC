import React, { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Plus,
  Trash2,
  Edit,
  Save,
  Grid,
  Package,
  Move,
  AlertCircle,
  Search,
  Pencil,
  Upload,
  Image,
  X,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { DragDropContext, Droppable, Draggable, DropResult } from "react-beautiful-dnd";
import { cn } from "@/lib/utils";
import { Product } from "@/types/product";
import { productService } from "@/services/productService";
import { planogramService } from "@/services/planogramService";
import { Planogram, PlanogramCreate, PlanogramSection, PlanogramShelf } from "@/types/planogram";
import { API_CONFIG } from "@/config/api";

export const PlanogramManager: React.FC = () => {
  const [planograms, setPlanograms] = useState<Planogram[]>([]);
  const [editingPlanogram, setEditingPlanogram] = useState<Planogram | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("layout");
  const [selectedProduct, setSelectedProduct] = useState<string>("");
  const [selectedVariant, setSelectedVariant] = useState<string>("");
  const [gridSize, setGridSize] = useState({ rows: 4, columns: 6 });
  const [error, setError] = useState<string | null>(null);
  const [planogramName, setPlanogramName] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAddProductDialogOpen, setIsAddProductDialogOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [newProduct, setNewProduct] = useState<Omit<Product, "id">>({
    name: "",
    variants: [""],
    category: "Beverages",
    description: "",
    brand: "",
    image_url: null,
  });
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [isDetectingGrid, setIsDetectingGrid] = useState(false);
  const [gridDetected, setGridDetected] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

  useEffect(() => {
    fetchPlanograms();
    fetchProducts();
  }, []);

  // Cleanup image URL on unmount
  useEffect(() => {
    return () => {
      if (uploadedImage) {
        URL.revokeObjectURL(uploadedImage);
      }
    };
  }, [uploadedImage]);

  const fetchProducts = async () => {
    try {
      setIsLoading(true);
      const data = await productService.listProducts();
      setProducts(data);
    } catch (error) {
      console.error("Error fetching products:", error);
      toast.error("Failed to fetch products");
    } finally {
      setIsLoading(false);
    }
  };

  const fetchPlanograms = async () => {
    try {
      const data = await planogramService.listPlanograms();
      setPlanograms(data);
    } catch (error) {
      console.error("Error fetching planograms:", error);
      toast.error("Failed to fetch planograms");
    }
  };

  const createEmptyPlanogram = (): Planogram => {
    const shelves = Array.from({ length: gridSize.rows }, (_, row) => ({
      row,
      sections: Array.from({ length: gridSize.columns }, (_, column) => ({
        column,
        expected_product: "",
        allowed_variants: [],
        min_quantity: 1,
        max_quantity: 1,
      })),
    }));

    return {
      id: "", // Empty ID for new planograms
      name: "",
      shelves,
    };
  };

  const handleAddPlanogram = () => {
    const newPlanogram = createEmptyPlanogram();
    setEditingPlanogram(newPlanogram);
    setIsDialogOpen(true);
    setActiveTab("layout");
    setError(null);
    setPlanogramName("");
    setUploadedImage(null);
    setImageFile(null);
    setGridDetected(false);
  };

  const handleImageUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith("image/")) {
      toast.error("Please upload a valid image file");
      return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      toast.error("Image size should be less than 10MB");
      return;
    }

    setImageFile(file);

    // Create preview URL
    const imageUrl = URL.createObjectURL(file);
    setUploadedImage(imageUrl);

    // Detect grid automatically
    await detectGrid(file);
  };

  const detectGrid = async (file: File) => {
    setIsDetectingGrid(true);
    setGridDetected(false);

    try {
      console.log("Starting grid detection for file:", file.name, "size:", file.size, "type:", file.type);

      const formData = new FormData();
      formData.append("image", file);

      const response = await fetch(API_CONFIG.getFullUrl("/detect-grid"), {
        method: "POST",
        body: formData,
      });

      console.log("Grid detection response status:", response.status);

      if (!response.ok) {
        let errorMessage = "Failed to detect grid";
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch {
          // If response is not JSON, try to get text
          const errorText = await response.text();
          errorMessage = errorText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const result = await response.json();
      console.log("Grid detection result:", result);

      if (!result.grid_dimensions) {
        throw new Error("No grid dimensions detected in the image");
      }

      const { rows, columns } = result.grid_dimensions;
      if (!rows || !columns || rows < 1 || columns < 1) {
        throw new Error("Invalid grid dimensions detected");
      }

      setGridSize({ rows, columns });

      // Update the planogram with detected grid size
      if (editingPlanogram) {
        const newShelves = Array.from({ length: rows }, (_, row) => ({
          row,
          sections: Array.from({ length: columns }, (_, column) => ({
            column,
            expected_product: "",
            allowed_variants: [],
            min_quantity: 1,
            max_quantity: 1,
          })),
        }));

        setEditingPlanogram({
          ...editingPlanogram,
          shelves: newShelves,
        });
      }

      setGridDetected(true);
      toast.success(`Grid detected: ${rows} rows × ${columns} columns`);
    } catch (error) {
      console.error("Grid detection error:", error);
      if (error instanceof Error) {
        toast.error(error.message);
      } else {
        toast.error("Failed to detect grid in the image");
      }
      setGridDetected(false);
    } finally {
      setIsDetectingGrid(false);
    }
  };

  const handleRemoveImage = () => {
    if (uploadedImage) {
      URL.revokeObjectURL(uploadedImage);
    }
    setUploadedImage(null);
    setImageFile(null);
    setGridDetected(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleEditPlanogram = (planogram: Planogram) => {
    setEditingPlanogram({ ...planogram });
    setIsDialogOpen(true);
    setActiveTab("layout");
    setError(null);
    setPlanogramName(planogram.name);
  };

  const handleDeletePlanogram = async (id: string) => {
    setIsDeleting(true);
    try {
      await planogramService.deletePlanogram(id);
      const updatedPlanograms = await planogramService.listPlanograms();
      setPlanograms(updatedPlanograms);
      window.dispatchEvent(new Event("planogram-dialog-close"));
      toast.success("Planogram deleted successfully");
    } catch (error) {
      console.error("Error deleting planogram:", error);
      toast.error("Failed to delete planogram");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleSavePlanogram = async () => {
    setIsSaving(true);
    try {
      if (!editingPlanogram) return;

      // Validate planogram name
      const name = planogramName.trim();
      if (!name) {
        setError("Please enter a planogram name");
        setIsSaving(false);
        return;
      }

      const planogramData: PlanogramCreate = {
        name: name,
        shelves: editingPlanogram.shelves,
      };

      // Check if we're editing an existing planogram by looking for it in the planograms list
      const existingPlanogram = planograms.find((p) => p.id === editingPlanogram.id);

      if (existingPlanogram) {
        await planogramService.updatePlanogram(editingPlanogram.id, planogramData);
        toast.success("Planogram updated successfully");
      } else {
        await planogramService.createPlanogram(planogramData);
        toast.success("Planogram created successfully");
      }

      // Get updated planogram list
      const updatedPlanograms = await planogramService.listPlanograms();
      setPlanograms(updatedPlanograms);

      // Reset form state
      setIsDialogOpen(false);
      setEditingPlanogram(null);
      setPlanogramName("");
      setUploadedImage(null);
      setImageFile(null);
      setGridDetected(false);
      setError(null);

      // Dispatch event to notify other components
      window.dispatchEvent(new Event("planogram-dialog-close"));
    } catch (error) {
      console.error("Error saving planogram:", error);
      if (error instanceof Error) {
        toast.error(`Failed to save planogram: ${error.message}`);
      } else {
        toast.error("Failed to save planogram. Please check the data and try again.");
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdateSection = (rowIndex: number, columnIndex: number, product: Product) => {
    if (!editingPlanogram) return;

    const updatedShelves = [...editingPlanogram.shelves];
    updatedShelves[rowIndex].sections[columnIndex] = {
      ...updatedShelves[rowIndex].sections[columnIndex],
      expected_product: product.name,
      allowed_variants: product.variants,
    };

    setEditingPlanogram({
      ...editingPlanogram,
      shelves: updatedShelves,
    });
  };

  const handleDragEnd = (result: DropResult) => {
    if (!result.destination || !editingPlanogram) return;

    const { source, destination } = result;
    const product = products.find((p) => p.id === result.draggableId);

    if (!product) return;

    const [destRow, destCol] = destination.droppableId.split("-").map(Number);
    handleUpdateSection(destRow, destCol, product);
  };

  const renderPlanogramGrid = () => {
    if (!editingPlanogram) return null;

    if (uploadedImage) {
      return (
        <div className="relative w-full h-auto max-w-2xl mx-auto">
          <img src={uploadedImage} alt="Shelf layout" className="w-full h-auto object-contain" />
          <div
            className="absolute inset-0 grid gap-1 p-1"
            style={{
              gridTemplateRows: `repeat(${gridSize.rows}, 1fr)`,
              gridTemplateColumns: `repeat(${gridSize.columns}, 1fr)`,
            }}
          >
            {editingPlanogram.shelves.map((shelf, rowIndex) =>
              shelf.sections.map((section, columnIndex) => (
                <Droppable key={`${rowIndex}-${columnIndex}`} droppableId={`${rowIndex}-${columnIndex}`}>
                  {(provided, snapshot) => (
                    <div
                      ref={provided.innerRef}
                      {...provided.droppableProps}
                      className={cn(
                        "border-2 border-dashed border-white/60 rounded-md flex items-center justify-center transition-all backdrop-blur-sm",
                        snapshot.isDraggingOver ? "bg-primary/30 border-primary border-solid" : "hover:bg-white/20",
                        section.expected_product && "bg-success/30 border-success border-solid"
                      )}
                      style={{
                        gridRow: rowIndex + 1,
                        gridColumn: columnIndex + 1,
                        minHeight: "25px",
                      }}
                    >
                      {section.expected_product ? (
                        <div className="flex flex-col items-center gap-1 p-1">
                          <div className="w-3 h-3 rounded-full bg-success/80 flex items-center justify-center">
                            <Package className="w-2 h-2 text-white" />
                          </div>
                          <span className="text-xs font-bold text-white bg-black/60 px-1 rounded text-center leading-tight">
                            {section.expected_product}
                          </span>
                        </div>
                      ) : (
                        <div className="text-xs text-white bg-black/60 px-1 py-1 rounded text-center">Drop</div>
                      )}
                      {provided.placeholder}
                    </div>
                  )}
                </Droppable>
              ))
            )}
          </div>
        </div>
      );
    }

    return (
      <div className="grid gap-2">
        {editingPlanogram.shelves.map((shelf, rowIndex) => (
          <div key={rowIndex} className="flex gap-2">
            {shelf.sections.map((section, columnIndex) => (
              <Droppable key={`${rowIndex}-${columnIndex}`} droppableId={`${rowIndex}-${columnIndex}`}>
                {(provided, snapshot) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.droppableProps}
                    className={cn(
                      "w-24 h-24 border rounded-lg flex items-center justify-center p-2 text-center transition-colors",
                      snapshot.isDraggingOver ? "bg-secondary border-primary" : "bg-muted",
                      section.expected_product && "bg-success/10 border-success"
                    )}
                  >
                    {section.expected_product ? (
                      <div className="flex flex-col items-center gap-1">
                        <Package className="w-6 h-6 text-success" />
                        <span className="text-xs font-medium">{section.expected_product}</span>
                        <Badge variant="secondary" className="text-xs bg-success/20 text-success hover:bg-success/30">
                          {section.allowed_variants.length} variants
                        </Badge>
                      </div>
                    ) : (
                      <div className="text-xs text-muted-foreground">Drop product here</div>
                    )}
                    {provided.placeholder}
                  </div>
                )}
              </Droppable>
            ))}
          </div>
        ))}
      </div>
    );
  };

  const handleAddProduct = async () => {
    if (!newProduct.name.trim()) {
      toast.error("Product name is required");
      return;
    }

    if (newProduct.variants.some((v) => !v.trim())) {
      toast.error("Variant names cannot be empty");
      return;
    }

    try {
      await productService.createProduct(newProduct);
      await fetchProducts();
      setIsAddProductDialogOpen(false);
      setNewProduct({
        name: "",
        variants: [""],
        category: "Beverages",
        description: "",
        brand: "",
        image_url: null,
      });
      toast.success("Product added successfully");
    } catch (error) {
      console.error("Error adding product:", error);
      toast.error("Failed to add product");
    }
  };

  const handleDeleteProduct = async (productId: string) => {
    // Check if product is used in any planogram
    const isUsed = editingPlanogram?.shelves.some((shelf) =>
      shelf.sections.some((section) => section.expected_product === products.find((p) => p.id === productId)?.name)
    );

    if (isUsed) {
      toast.error("Cannot delete product as it is being used in the current planogram");
      return;
    }

    try {
      await productService.deleteProduct(productId);
      await fetchProducts();
      toast.success("Product deleted successfully");
    } catch (error) {
      console.error("Error deleting product:", error);
      toast.error("Failed to delete product");
    }
  };

  const handleAddVariant = () => {
    setNewProduct((prev) => ({
      ...prev,
      variants: [...prev.variants, ""],
    }));
  };

  const handleRemoveVariant = (index: number) => {
    setNewProduct((prev) => ({
      ...prev,
      variants: prev.variants.filter((_, i) => i !== index),
    }));
  };

  const handleVariantChange = (index: number, value: string) => {
    setNewProduct((prev) => ({
      ...prev,
      variants: prev.variants.map((v, i) => (i === index ? value : v)),
    }));
  };

  const handleSearchProducts = async (query: string) => {
    setSearchQuery(query);
    if (query.trim()) {
      try {
        const results = await productService.searchProducts(query);
        setProducts(results);
      } catch (error) {
        console.error("Error searching products:", error);
      }
    } else {
      fetchProducts();
    }
  };

  const renderProductList = () => {
    return (
      <div className="space-y-4">
        <div className="space-y-2">
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search products..."
              value={searchQuery}
              onChange={(e) => handleSearchProducts(e.target.value)}
              className="pl-8 bg-muted border-0 focus-visible:ring-1 focus-visible:ring-primary"
            />
          </div>
        </div>
        <Droppable droppableId="productList" isDropDisabled={true}>
          {(provided) => (
            <div ref={provided.innerRef} {...provided.droppableProps} className="grid grid-cols-2 gap-3">
              {products.map((product, index) => (
                <Draggable key={product.id} draggableId={product.id} index={index}>
                  {(provided, snapshot) => (
                    <div
                      ref={provided.innerRef}
                      {...provided.draggableProps}
                      {...provided.dragHandleProps}
                      className={cn("transition-all", snapshot.isDragging && "scale-105")}
                    >
                      <Card className="cursor-move hover:border-primary transition-colors bg-card">
                        <CardContent className="p-3">
                          <div className="flex items-center gap-3">
                            <Move className="w-4 h-4 text-primary" />
                            <div>
                              <p className="font-medium text-sm">{product.name}</p>
                              <p className="text-xs text-muted-foreground">{product.variants.join(", ")}</p>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  )}
                </Draggable>
              ))}
              {provided.placeholder}
            </div>
          )}
        </Droppable>
      </div>
    );
  };

  const renderProductsTab = () => {
    return (
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <Button onClick={() => setIsAddProductDialogOpen(true)} className="gap-2 bg-primary hover:bg-primary/90">
            <Plus className="w-4 h-4" />
            Add Product
          </Button>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="bg-card border-border">
                <CardHeader className="pb-3">
                  <div className="h-6 bg-muted animate-pulse rounded" />
                </CardHeader>
                <CardContent className="pb-3">
                  <div className="space-y-2">
                    <div className="h-4 bg-muted animate-pulse rounded w-1/3" />
                    <div className="h-4 bg-muted animate-pulse rounded w-2/3" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : products.length === 0 ? (
          <div className="text-center py-8">
            <Package className="w-12 h-12 text-muted-foreground mx-auto mb-3" />
            <h3 className="text-lg font-medium mb-2">No products found</h3>
            <p className="text-sm text-muted-foreground mb-4">Get started by adding your first product</p>
            <Button onClick={() => setIsAddProductDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add Product
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            {products.map((product) => (
              <Card key={product.id} className="bg-card border-border hover:border-primary/50 transition-colors">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center justify-between">
                    {product.name}
                    <Badge variant="outline" className="text-xs">
                      {product.brand}
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pb-3">
                  <div className="space-y-3 text-sm text-muted-foreground">
                    {product.description && <p className="text-xs">{product.description}</p>}
                    <div>
                      <p className="font-medium text-xs uppercase tracking-wide mb-1">Category</p>
                      <Badge variant="secondary" className="text-xs">
                        {product.category}
                      </Badge>
                    </div>
                    <div>
                      <p className="font-medium text-xs uppercase tracking-wide mb-1">Variants</p>
                      <div className="flex flex-wrap gap-1">
                        {product.variants?.map((variant, idx) => (
                          <Badge key={idx} variant="secondary" className="text-xs bg-secondary/50">
                            {variant}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                </CardContent>
                <CardFooter className="flex justify-end gap-2 pt-0">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                    onClick={() => handleDeleteProduct(product.id)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}

        <Dialog open={isAddProductDialogOpen} onOpenChange={setIsAddProductDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add New Product</DialogTitle>
              <DialogDescription>
                Add a new product to your inventory. Fill in the product details and variants below.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="name">Product Name</Label>
                <Input
                  id="name"
                  value={newProduct.name}
                  onChange={(e) => setNewProduct((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="Enter product name"
                />
              </div>
              <div>
                <Label htmlFor="brand">Brand</Label>
                <Input
                  id="brand"
                  value={newProduct.brand}
                  onChange={(e) => setNewProduct((prev) => ({ ...prev, brand: e.target.value }))}
                  placeholder="Enter brand name"
                />
              </div>
              <div>
                <Label htmlFor="category">Category</Label>
                <Select
                  value={newProduct.category}
                  onValueChange={(value) => setNewProduct((prev) => ({ ...prev, category: value }))}
                >
                  <SelectTrigger id="category">
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Beverages">Beverages</SelectItem>
                    <SelectItem value="Snacks">Snacks</SelectItem>
                    <SelectItem value="Dairy">Dairy</SelectItem>
                    <SelectItem value="Other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="description">Description</Label>
                <Input
                  id="description"
                  value={newProduct.description}
                  onChange={(e) => setNewProduct((prev) => ({ ...prev, description: e.target.value }))}
                  placeholder="Enter product description"
                />
              </div>
              <div>
                <Label>Variants</Label>
                <div className="space-y-2">
                  {newProduct.variants.map((variant, index) => (
                    <div key={index} className="flex gap-2">
                      <Input
                        id={`variant-${index}`}
                        value={variant}
                        onChange={(e) => handleVariantChange(index, e.target.value)}
                        placeholder={`Variant ${index + 1}`}
                        aria-label={`Variant ${index + 1}`}
                      />
                      {newProduct.variants.length > 1 && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleRemoveVariant(index)}
                          className="hover:bg-destructive/10 hover:text-destructive"
                          aria-label={`Remove variant ${index + 1}`}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  ))}
                  <Button type="button" variant="outline" size="sm" onClick={handleAddVariant} className="w-full">
                    <Plus className="h-4 w-4 mr-2" />
                    Add Variant
                  </Button>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsAddProductDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleAddProduct}>Add Product</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    );
  };

  const handleGridSizeChange = (type: "rows" | "columns", value: string) => {
    const numValue = parseInt(value, 10);
    if (numValue > 0 && numValue <= 12) {
      setGridSize((prev) => ({
        ...prev,
        [type]: numValue,
      }));

      // Update existing planogram with new grid size
      if (editingPlanogram) {
        const newShelves = Array.from({ length: type === "rows" ? numValue : gridSize.rows }, (_, row) => ({
          row,
          sections: Array.from({ length: type === "columns" ? numValue : gridSize.columns }, (_, column) => {
            // Preserve existing section data if available
            const existingSection = editingPlanogram.shelves[row]?.sections[column];
            return (
              existingSection || {
                column,
                expected_product: "",
                allowed_variants: [],
                min_quantity: 1,
                max_quantity: 1,
              }
            );
          }),
        }));

        setEditingPlanogram({
          ...editingPlanogram,
          shelves: newShelves,
        });
      }
    }
  };

  const handleDragStart = (event: React.DragEvent<HTMLDivElement>, product: Product) => {
    event.dataTransfer.setData("application/json", JSON.stringify(product));
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-semibold">Your Planograms</h2>
          <p className="text-sm text-muted-foreground">Create and manage your shelf planograms</p>
        </div>
        <Button onClick={handleAddPlanogram} size="lg" className="gap-2 bg-primary hover:bg-primary/90">
          <Plus className="w-5 h-5" />
          Create New Planogram
        </Button>
      </div>

      <Dialog
        open={isDialogOpen}
        onOpenChange={(open) => {
          setIsDialogOpen(open);
          if (!open) {
            handleRemoveImage();
            setEditingPlanogram(null);
            setError(null);
            setActiveTab("layout");
            setPlanogramName("");
            setGridDetected(false);
            fetchPlanograms(); // Always refresh the list when dialog closes
            // Dispatch event for other components to refresh their planogram lists
            window.dispatchEvent(new Event("planogram-dialog-close"));
          }
        }}
      >
        <DialogContent className="max-w-[95vw] w-full max-h-[95vh] flex flex-col gap-0 p-0 bg-background">
          <DialogHeader className="px-6 py-4 border-b flex-shrink-0">
            <DialogTitle>{editingPlanogram ? "Edit Planogram" : "Create New Planogram"}</DialogTitle>
            <DialogDescription>Design your planogram layout and assign products to shelf positions.</DialogDescription>
          </DialogHeader>

          <div className="flex-1 min-h-0 overflow-y-auto">
            <div className="space-y-0">
              <div className="px-6 py-4 space-y-4 border-b flex-shrink-0">
                <div>
                  <Label htmlFor="planogramName">Planogram Name</Label>
                  <Input
                    id="planogramName"
                    value={planogramName}
                    onChange={(e) => {
                      setPlanogramName(e.target.value);
                      if (error && e.target.value.trim()) {
                        setError(null); // Clear error when user starts typing a valid name
                      }
                    }}
                    placeholder="Enter planogram name"
                    className="bg-muted border-0 focus-visible:ring-1 focus-visible:ring-primary"
                  />
                  {error && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}
                </div>

                <div>
                  <Label htmlFor="rows" className="text-sm">
                    Grid Size{" "}
                    {gridDetected && (
                      <Badge variant="secondary" className="ml-2 bg-success/20 text-success">
                        Auto-detected
                      </Badge>
                    )}
                  </Label>
                  <div className="flex items-center gap-3">
                    <div className="w-28">
                      <Select
                        value={gridSize.rows.toString()}
                        onValueChange={(value) => handleGridSizeChange("rows", value)}
                        disabled={isDetectingGrid}
                      >
                        <SelectTrigger className="bg-muted border-0 focus:ring-1 focus:ring-primary">
                          <SelectValue placeholder="Rows" />
                        </SelectTrigger>
                        <SelectContent>
                          {Array.from({ length: 12 }, (_, i) => i + 1).map((num) => (
                            <SelectItem key={num} value={num.toString()}>
                              {num} {num === 1 ? "row" : "rows"}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <span className="text-sm text-muted-foreground">×</span>
                    <div className="w-28">
                      <Select
                        value={gridSize.columns.toString()}
                        onValueChange={(value) => handleGridSizeChange("columns", value)}
                        disabled={isDetectingGrid}
                      >
                        <SelectTrigger className="bg-muted border-0 focus:ring-1 focus:ring-primary">
                          <SelectValue placeholder="Columns" />
                        </SelectTrigger>
                        <SelectContent>
                          {Array.from({ length: 12 }, (_, i) => i + 1).map((num) => (
                            <SelectItem key={num} value={num.toString()}>
                              {num} {num === 1 ? "column" : "columns"}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                <div>
                  <Label className="text-sm">Shelf Image (Optional)</Label>
                  <p className="text-xs text-muted-foreground mb-3">
                    Upload an image of your shelf to automatically detect the grid layout
                  </p>

                  {!uploadedImage ? (
                    <div
                      className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-6 text-center cursor-pointer hover:border-primary/50 hover:bg-muted/50 transition-colors"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <Upload className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                      <p className="text-sm text-muted-foreground mb-1">Click to upload shelf image</p>
                      <p className="text-xs text-muted-foreground">PNG, JPG, JPEG up to 10MB</p>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*"
                        onChange={handleImageUpload}
                        className="hidden"
                      />
                    </div>
                  ) : (
                    <div className="relative">
                      <div className="border rounded-lg p-3 bg-muted/30">
                        <div className="flex items-center gap-3">
                          <div className="w-12 h-12 rounded-lg overflow-hidden bg-muted">
                            <img src={uploadedImage} alt="Uploaded shelf" className="w-full h-full object-cover" />
                          </div>
                          <div className="flex-1">
                            <p className="text-sm font-medium">Shelf image uploaded</p>
                            <div className="flex items-center gap-2">
                              {isDetectingGrid ? (
                                <div className="flex items-center gap-2">
                                  <div className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                                  <span className="text-xs text-muted-foreground">Detecting grid...</span>
                                </div>
                              ) : gridDetected ? (
                                <Badge variant="secondary" className="bg-success/20 text-success">
                                  Grid detected: {gridSize.rows}×{gridSize.columns}
                                </Badge>
                              ) : (
                                <Badge variant="secondary" className="bg-destructive/20 text-destructive">
                                  Grid detection failed
                                </Badge>
                              )}
                            </div>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={handleRemoveImage}
                            className="h-8 w-8 p-0 hover:bg-destructive/10 hover:text-destructive"
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="min-h-[600px]">
                <Tabs defaultValue="layout" className="flex flex-col">
                  <div className="px-6 border-b flex-shrink-0">
                    <TabsList className="bg-muted h-10 w-fit">
                      <TabsTrigger value="layout" className="data-[state=active]:bg-background">
                        Layout Design
                      </TabsTrigger>
                      <TabsTrigger value="products" className="data-[state=active]:bg-background">
                        Products
                      </TabsTrigger>
                    </TabsList>
                  </div>

                  <div className="flex-1">
                    <TabsContent value="layout" className="m-0 border-0">
                      <DragDropContext onDragEnd={handleDragEnd}>
                        <div className="flex gap-6 min-h-[600px]">
                          <div className="flex-1 p-6">
                            <div className="w-full h-[550px] border rounded-lg bg-slate-100 dark:bg-slate-800 p-4">
                              <div className="w-full h-full">{renderPlanogramGrid()}</div>
                            </div>
                          </div>
                          <div className="w-96 border-l">
                            <div className="p-6">
                              <h3 className="font-medium mb-3">Available Products</h3>
                              <div className="h-[500px] overflow-y-auto pr-2">{renderProductList()}</div>
                            </div>
                          </div>
                        </div>
                      </DragDropContext>
                    </TabsContent>

                    <TabsContent value="products" className="m-0 border-0">
                      <div className="p-6 min-h-[600px]">
                        <div className="h-[550px] overflow-y-auto pr-2">{renderProductsTab()}</div>
                      </div>
                    </TabsContent>
                  </div>
                </Tabs>
              </div>
            </div>
          </div>

          <DialogFooter className="px-6 py-4 border-t bg-background mt-auto flex-shrink-0">
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={async () => {
                  setIsDialogOpen(false);
                  handleRemoveImage();
                  setEditingPlanogram(null);
                  setError(null);
                  setActiveTab("layout");
                  setPlanogramName("");
                  setGridDetected(false);
                  await fetchPlanograms(); // Refresh list when canceling
                }}
                className="border-0 bg-muted hover:bg-muted/80"
              >
                Cancel
              </Button>
              <Button
                onClick={handleSavePlanogram}
                disabled={!planogramName}
                className="bg-primary hover:bg-primary/90"
              >
                Save Planogram
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {planograms.length === 0 ? (
        <div className="border-2 border-dashed rounded-lg p-12 text-center">
          <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
            <Package className="w-6 h-6 text-primary" />
          </div>
          <h3 className="text-lg font-medium mb-2">No planograms yet</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Create your first planogram to start managing your shelf layouts
          </p>
          <Button onClick={handleAddPlanogram} className="gap-2 bg-primary hover:bg-primary/90">
            <Plus className="w-4 h-4" />
            Create New Planogram
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {planograms.map((planogram) => (
            <Card
              key={planogram.id}
              className="bg-card hover:border-primary/50 transition-colors h-[400px] flex flex-col overflow-hidden"
            >
              <CardHeader className="pb-3 flex-shrink-0 border-b">
                <CardTitle className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Grid className="w-5 h-5 text-primary" />
                    <span className="text-lg">{planogram.name}</span>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEditPlanogram(planogram)}
                      className="h-8 w-8 p-0 hover:bg-primary/10 hover:text-primary"
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 hover:bg-destructive/10 hover:text-destructive"
                      onClick={() => handleDeletePlanogram(planogram.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardTitle>
                <div className="flex items-center gap-4 mt-1">
                  <Badge variant="secondary" className="bg-primary/10 text-primary hover:bg-primary/20">
                    {planogram.shelves.length} {planogram.shelves.length === 1 ? "shelf" : "shelves"}
                  </Badge>
                  <Badge variant="secondary" className="bg-primary/10 text-primary hover:bg-primary/20">
                    {planogram.shelves.reduce((acc, shelf) => acc + shelf.sections.length, 0)} sections
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="flex-1 min-h-0 p-0">
                <ScrollArea className="h-full">
                  <div className="space-y-2 p-6">
                    {planogram.shelves.map((shelf, shelfIndex) => (
                      <div key={shelfIndex} className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0 border">
                          <span className="text-sm font-medium">{shelf.row + 1}</span>
                        </div>
                        <ScrollArea className="w-full rounded-lg border bg-muted/30 p-2">
                          <div
                            className="flex gap-2"
                            style={{
                              minWidth: `${
                                Math.max(
                                  ...planogram.shelves.map((s) => Math.max(...s.sections.map((sec) => sec.column)) + 1)
                                ) * 40
                              }px`,
                              width: `${
                                Math.max(
                                  ...planogram.shelves.map((s) => Math.max(...s.sections.map((sec) => sec.column)) + 1)
                                ) * 40
                              }px`,
                            }}
                          >
                            {shelf.sections.map((section, sectionIndex) => (
                              <div
                                key={sectionIndex}
                                className="w-10 h-10 rounded-md bg-background border shadow-sm relative group hover:border-primary hover:shadow-md transition-all flex-shrink-0"
                                style={{ order: section.column }}
                              >
                                {section.expected_product ? (
                                  <div className="absolute inset-0 flex items-center justify-center">
                                    <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
                                      <Package className="w-4 h-4 text-primary" />
                                    </div>
                                  </div>
                                ) : (
                                  <div className="absolute inset-0 flex items-center justify-center">
                                    <div className="w-6 h-6 rounded-full bg-muted flex items-center justify-center">
                                      <span className="text-xs text-muted-foreground">E</span>
                                    </div>
                                  </div>
                                )}
                                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-primary/90 rounded-md transition-all">
                                  <span className="text-[10px] text-white text-center px-1 font-medium">
                                    {section.expected_product || "Empty"}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </ScrollArea>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
