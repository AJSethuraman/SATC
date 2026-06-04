'use client';

import Tooltip from './Tooltip';

interface NumberInputProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  prefix?: string;
  suffix?: string;
  step?: number;
  min?: number;
  max?: number;
  tooltip?: string;
  hint?: string;
}

export default function NumberInput({
  label,
  value,
  onChange,
  prefix,
  suffix,
  step = 1,
  min = 0,
  max,
  tooltip,
  hint,
}: NumberInputProps) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-sm font-medium text-gray-700">{label}</label>
        {tooltip && <Tooltip text={tooltip} />}
      </div>

      <div className="flex rounded-lg border border-gray-300 overflow-hidden focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500 transition-shadow">
        {prefix && (
          <span className="flex items-center px-3 bg-gray-50 border-r border-gray-200 text-gray-500 text-sm select-none">
            {prefix}
          </span>
        )}
        <input
          type="number"
          value={value}
          onChange={(e) => {
            const n = parseFloat(e.target.value);
            onChange(isNaN(n) ? 0 : max !== undefined ? Math.min(max, Math.max(min, n)) : Math.max(min, n));
          }}
          step={step}
          min={min}
          max={max}
          className="flex-1 px-3 py-2 text-gray-900 text-sm bg-white outline-none w-full"
        />
        {suffix && (
          <span className="flex items-center px-3 bg-gray-50 border-l border-gray-200 text-gray-500 text-sm select-none">
            {suffix}
          </span>
        )}
      </div>

      {hint && <p className="mt-1 text-xs text-blue-600 font-medium">{hint}</p>}
    </div>
  );
}
