import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Rental Property Cash Flow Calculator | Is This Investment Worth It?',
  description:
    'Calculate monthly cash flow, cap rate, and ROI for any rental property in seconds. Free investment property calculator — no sign-up required.',
  keywords: [
    'rental property calculator',
    'investment property calculator',
    'cash flow calculator',
    'cap rate calculator',
    'real estate ROI calculator',
    'landlord calculator',
  ],
  openGraph: {
    title: 'Rental Property Cash Flow Calculator',
    description:
      'Find out instantly if a rental property will make you money. Enter any address and get your monthly cash flow, cap rate, and more.',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/*
          ── Google AdSense ──
          Replace YOUR_PUBLISHER_ID below and uncomment to enable ads.

          <script
            async
            src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-YOUR_PUBLISHER_ID"
            crossOrigin="anonymous"
          />
        */}
      </head>
      <body className="min-h-screen flex flex-col">{children}</body>
    </html>
  );
}
