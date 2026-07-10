'use client';

import { useState } from 'react';

export default function Tooltip({ text }: { text: string }) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="relative inline-block">
      <button
        type="button"
        aria-label="More info"
        className="w-4 h-4 rounded-full bg-gray-200 text-gray-500 text-xs font-bold flex items-center justify-center hover:bg-blue-100 hover:text-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-400 transition-colors"
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
      >
        ?
      </button>

      {visible && (
        <div
          role="tooltip"
          className="absolute right-0 top-6 z-20 w-64 rounded-xl bg-gray-800 text-white text-xs leading-relaxed p-3 shadow-xl"
        >
          <div className="absolute -top-1.5 right-1 w-3 h-3 bg-gray-800 rotate-45 rounded-sm" />
          {text}
        </div>
      )}
    </div>
  );
}
