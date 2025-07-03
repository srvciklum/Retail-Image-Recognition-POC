import React, { useEffect, useState } from "react";
import thresholds from "@/data/thresholds.json";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ShoppingCart, AlertTriangle } from "lucide-react";

interface DetectedCounts {
  [item: string]: number;
}

interface Product {
  item: string;
  count: number;
  threshold: number;
  shouldOrder: boolean;
}

interface ProductTableProps {
  detectedCounts: DetectedCounts;
  emptyShelfItems: string[];
}

const DEFAULT_THRESHOLD = 10;

const handleOrder = (itemName: string) => {
  alert(`Order placed for ${itemName}`);
  // Optional: Add actual API call logic here.
};

export const ProductTable: React.FC<ProductTableProps> = ({ detectedCounts, emptyShelfItems }) => {
  const [products, setProducts] = useState<Product[]>([]);

  useEffect(() => {
    const items: Product[] = Object.entries(detectedCounts)
      .filter(([item]) => item.toLowerCase() !== "emptyspace")
      .map(([item, count]) => {
        const threshold = (thresholds as Record<string, number>)[item.toLowerCase()] ?? DEFAULT_THRESHOLD;
        return {
          item,
          count,
          threshold,
          shouldOrder: count <= threshold,
        };
      });
    setProducts(items);
  }, [detectedCounts]);

  return (
    <div className="space-y-8">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShoppingCart className="w-5 h-5" />
            Inventory Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Product</TableHead>
                <TableHead className="text-center">Count</TableHead>
                <TableHead className="text-center">Threshold</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {products.map(({ item, count, threshold, shouldOrder }) => (
                <TableRow key={item}>
                  <TableCell className="font-medium capitalize">{item}</TableCell>
                  <TableCell className="text-center">
                    <Badge variant={shouldOrder ? "destructive" : "secondary"}>{count}</Badge>
                  </TableCell>
                  <TableCell className="text-center text-muted-foreground">{threshold}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant={shouldOrder ? "default" : "secondary"}
                      size="sm"
                      disabled={!shouldOrder}
                      onClick={() => handleOrder(item)}
                    >
                      {shouldOrder ? "Order Now" : "In Stock"}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {emptyShelfItems.length > 0 && (
        <Card className="border-red-100">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="w-5 h-5" />
              Empty Shelf Items
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3">
              {emptyShelfItems.map((item, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-red-50/50 rounded-lg border border-red-100"
                >
                  <div className="flex items-center gap-2">
                    <Badge variant="destructive" className="uppercase">
                      Empty
                    </Badge>
                    <span className="font-medium">{item}</span>
                  </div>
                  <Button size="sm" onClick={() => handleOrder(item)} className="bg-red-600 hover:bg-red-700">
                    Order Now
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
