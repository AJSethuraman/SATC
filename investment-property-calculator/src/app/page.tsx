import Calculator from '@/components/Calculator';
import AdUnit from '@/components/AdUnit';

export default function Home() {
  return (
    <>
      {/* ── Header ── */}
      <header className="bg-white border-b border-gray-100 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">
              Rental Property Calculator
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Find out instantly if a rental property will make you money.
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 text-xs font-medium bg-emerald-100 text-emerald-700 px-3 py-1.5 rounded-full self-start sm:self-auto">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
            Free · No sign-up
          </span>
        </div>
      </header>

      {/* ── Top Ad Banner ── */}
      <div className="bg-white border-b border-gray-100 py-3 px-4">
        <AdUnit size="leaderboard" />
      </div>

      {/* ── Main Calculator ── */}
      <main className="flex-1">
        <Calculator />

        {/* ── FAQ / Education Section ── */}
        <section
          id="faq"
          aria-labelledby="faq-heading"
          className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12"
        >
          <h2
            id="faq-heading"
            className="text-2xl font-bold text-gray-900 mb-8 text-center"
          >
            Common Questions From New Investors
          </h2>

          <div className="space-y-6">
            <FaqItem
              q="What's a good monthly cash flow for a rental property?"
              a="Any positive cash flow is technically a win, but most investors aim for at least $100–$300 per month per property after all expenses. In expensive markets, even $50/month can be acceptable if you expect strong appreciation. The important thing is that you're not losing money every month."
            />
            <FaqItem
              q="What is the 1% rule, and does it still work?"
              a="The 1% rule says your monthly rent should be at least 1% of the purchase price — for example, a $250,000 property should rent for at least $2,500/month. It's a quick back-of-napkin filter, not a guarantee. In high cost-of-living cities it's nearly impossible to meet, but properties that clear it usually produce positive cash flow more easily."
            />
            <FaqItem
              q="What is cap rate, and what's a good number?"
              a="Cap rate (capitalization rate) measures a property's income return before financing. It's simply the annual net operating income divided by the purchase price. A cap rate of 5–8% is generally considered solid for residential rentals in most U.S. markets. Higher cap rates often mean higher-risk areas; lower cap rates are common in expensive, stable markets."
            />
            <FaqItem
              q="What is cash-on-cash return?"
              a="Cash-on-cash return is the annual cash profit divided by the total cash you put in (down payment + closing costs). Unlike cap rate, it accounts for your mortgage. Think of it like the interest rate your down payment earns you. Many investors target 8–12% or better, though anything above 6–7% in a stable market is often acceptable."
            />
            <FaqItem
              q="How much should I budget for repairs and maintenance?"
              a="A widely used rule of thumb is 1% of the property's value per year — so a $250,000 home budgets $2,500/year ($208/month). Older homes, cheaper properties, or properties with pools/older systems may need more. New construction typically needs less in the early years. Under-budgeting here is one of the most common mistakes new landlords make."
            />
            <FaqItem
              q="Should I include vacancy in my calculation?"
              a="Absolutely. Even a great property won't be rented 365 days a year. Tenants move out, units need cleaning and repairs between tenants, and it takes time to find a new renter. A 5% vacancy rate means about 18 days per year of no income — conservative but realistic. In soft rental markets, budget 8–10%."
            />
          </div>
        </section>

        {/* ── Bottom Ad ── */}
        <div className="py-6 px-4 bg-white border-t border-gray-100">
          <AdUnit size="leaderboard" />
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="bg-gray-800 text-gray-400 py-8 px-4">
        <div className="max-w-7xl mx-auto text-center text-sm space-y-2">
          <p className="font-medium text-gray-200">Rental Property Calculator</p>
          <p>
            Results are estimates for educational purposes only. Consult a licensed financial
            advisor, real estate professional, or accountant before making investment decisions.
          </p>
          <p className="text-xs text-gray-500">
            &copy; {new Date().getFullYear()} · All calculations performed locally in your browser.
            No data is stored or transmitted.
          </p>
        </div>
      </footer>
    </>
  );
}

function FaqItem({ q, a }: { q: string; a: string }) {
  return (
    <details className="bg-white rounded-2xl border border-gray-100 shadow-sm group" open={false}>
      <summary className="flex items-center justify-between cursor-pointer list-none px-6 py-4 font-medium text-gray-900 hover:text-blue-600 transition-colors select-none">
        <span>{q}</span>
        <span className="ml-4 shrink-0 text-gray-400 group-open:rotate-180 transition-transform duration-200">
          ▾
        </span>
      </summary>
      <div className="px-6 pb-5 text-sm text-gray-600 leading-relaxed">{a}</div>
    </details>
  );
}
