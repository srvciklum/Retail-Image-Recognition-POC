// react-image-exchange-main/src/components/Sidebar.tsx
import React from 'react';

const Sidebar = () => {
  return (
    <div className="p-4 text-sm text-gray-800 space-y-5">
      <h2 className="text-lg font-bold mb-2">📘 How It Works</h2>
      <ul className="space-y-4 list-none">
        <li>📸 Upload a shelf image to detect drink products.</li>
        <li>🤖 YOLOv8 model counts and identifies items.</li>
        <li>📉 Flags empty shelf spaces and low-stock items.</li>
        <li>🚨 Alerts for low stock via thresholds.</li>
      </ul>
    </div>
  );
};

export default Sidebar;

