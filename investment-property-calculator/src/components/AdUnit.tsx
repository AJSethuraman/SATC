'use client';

interface AdUnitProps {
  size: 'leaderboard' | 'rectangle' | 'banner';
  className?: string;
}

const SIZES: Record<AdUnitProps['size'], { container: string; label: string }> = {
  leaderboard: {
    container: 'h-24 w-full',
    label: '728 × 90 — Leaderboard',
  },
  rectangle: {
    container: 'h-64 w-full max-w-xs mx-auto',
    label: '300 × 250 — Medium Rectangle',
  },
  banner: {
    container: 'h-16 w-full',
    label: '468 × 60 — Banner',
  },
};

export default function AdUnit({ size, className = '' }: AdUnitProps) {
  const { container, label } = SIZES[size];

  return (
    <div
      className={`${container} ${className} bg-gray-100 border-2 border-dashed border-gray-300 rounded-xl flex flex-col items-center justify-center gap-1`}
      aria-hidden="true"
    >
      <span className="text-xs font-medium text-gray-400 uppercase tracking-widest">
        Advertisement
      </span>
      <span className="text-xs text-gray-300">{label}</span>
      {/*
        ── Replace this entire component with your AdSense ins tag, e.g.: ──

        <ins
          className="adsbygoogle"
          style={{ display: 'block' }}
          data-ad-client="ca-pub-YOUR_PUBLISHER_ID"
          data-ad-slot="YOUR_AD_SLOT_ID"
          data-ad-format="auto"
          data-full-width-responsive="true"
        />
        <Script id={`adsense-${size}`} strategy="afterInteractive">
          {`(adsbygoogle = window.adsbygoogle || []).push({});`}
        </Script>
      */}
    </div>
  );
}
