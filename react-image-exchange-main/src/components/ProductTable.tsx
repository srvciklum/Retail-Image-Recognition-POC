import React, { useEffect, useState } from 'react';
import thresholds from '../data/thresholds.json';
import '../ProductTable.css'

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

const handleOrder = (itemName: string) => {
  alert(`Order placed for ${itemName}`);
  // Optional: Add actual API call logic here.
};

const ProductTable: React.FC<ProductTableProps> = ({ detectedCounts, emptyShelfItems }) => {
  const [products, setProducts] = useState<Product[]>([]);

  useEffect(() => {
    const items: Product[] = Object.entries(detectedCounts)
    .filter(([item]) => item.toLowerCase() !== 'emptyspace')
    .map(([item, count]) => {
      const threshold = thresholds[item] ?? 10;
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
    <div className="max-w-2xl mx-auto p-4 border rounded-lg shadow">
      <h2 className="text-lg font-semibold mb-3">Detected Product Counts</h2>
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-gray-200">
            <th className="border px-3 py-2">Product</th>
            <th className="border px-3 py-2">Count</th>
            <th className="border px-3 py-2">Threshold</th>
            <th className="border px-3 py-2">Action</th>
          </tr>
        </thead>
        <tbody>
          {products.map(({ item, count, threshold, shouldOrder }) => (
            <tr key={item}>
              <td className="border px-3 py-2 capitalize">{item}</td>
              <td className="border px-3 py-2 text-center">{count}</td>
              <td className="border px-3 py-2 text-center">{threshold}</td>
              <td className="border px-3 py-2 text-center">
                <button
                  disabled={!shouldOrder}
                  onClick={() => handleOrder(item)}
                  className={`px-2 py-1 rounded text-white text-xs ${
                    shouldOrder ? 'bg-blue-600 hover:bg-blue-700' : 'bg-gray-400 cursor-not-allowed'
                  }`}
                >
                  Click to Order
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

{emptyShelfItems.length > 0 && (
  <div className="mt-6">
    <h2 className="text-lg font-semibold mb-3">🚫 Empty Shelf Items</h2>
    <ul className="space-y-3">
      {emptyShelfItems.map((item, index) => (
        <li
          key={index}
          className="flex items-center justify-between bg-white shadow-md px-4 py-2 rounded-lg border border-gray-200"
        >
          <span className="text-gray-800 font-medium">{item}</span>
          <button
            onClick={() => handleOrder(item)}
            className="px-2 py-1 rounded text-white text-xs bg-blue-600 hover:bg-blue-700"
          >
            Click to Order
          </button>
        </li>
      ))}
    </ul>
  </div>
)}

</div>
)};

export default ProductTable;
