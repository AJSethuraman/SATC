'use client';

import { useMemo, useState } from 'react';
import NumberInput from './NumberInput';
import AdUnit from './AdUnit';

interface Inputs {
  purchasePrice: number;
  downPaymentPercent: number;
  interestRate: number;
  loanTermYears: number;
  closingCostsPercent: number;
  monthlyRent: number;
  vacancyRatePercent: number;
  propertyTaxMonthly: number;
  insuranceMonthly: number;
  maintenanceMonthly: number;
  hoaMonthly: number;
  managementFeePercent: number;
  otherMonthly: number;
}

const DEFAULTS: Inputs = {
  purchasePrice: 250000,
  downPaymentPercent: 20,
  interestRate: 7.0,
  loanTermYears: 30,
  closingCostsPercent: 3,
  monthlyRent: 2000,
  vacancyRatePercent: 5,
  propertyTaxMonthly: 250,
  insuranceMonthly: 125,
  maintenanceMonthly: 208,
  hoaMonthly: 0,
  managementFeePercent: 0,
  otherMonthly: 0,
};

function calcMonthlyMortgage(principal: number, annualRatePct: number, years: number): number {
  if (principal <= 0) return 0;
  if (annualRatePct === 0) return principal / (years * 12);
  const r = annualRatePct / 100 / 12;
  const n = years * 12;
  return (principal * (r * Math.pow(1 + r, n))) / (Math.pow(1 + r, n) - 1);
}

const usd = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

const fmt = (n: number) => usd.format(n);
const fmtPct = (n: number) => `${n.toFixed(2)}%`;

export default function Calculator() {
  const [inputs, setInputs] = useState<Inputs>(DEFAULTS);

  const set = (field: keyof Inputs) => (value: number) =>
    setInputs((prev) => ({ ...prev, [field]: value }));

  const r = useMemo(() => {
    const downPayment = inputs.purchasePrice * (inputs.downPaymentPercent / 100);
    const loanAmount = inputs.purchasePrice - downPayment;
    const closingCosts = inputs.purchasePrice * (inputs.closingCostsPercent / 100);
    const totalCashInvested = downPayment + closingCosts;

    const monthlyMortgage = calcMonthlyMortgage(loanAmount, inputs.interestRate, inputs.loanTermYears);

    const effectiveMonthlyRent = inputs.monthlyRent * (1 - inputs.vacancyRatePercent / 100);
    const managementFeeMonthly = inputs.monthlyRent * (inputs.managementFeePercent / 100);

    const operatingExpenses =
      inputs.propertyTaxMonthly +
      inputs.insuranceMonthly +
      inputs.maintenanceMonthly +
      inputs.hoaMonthly +
      managementFeeMonthly +
      inputs.otherMonthly;

    const monthlyCashFlow = effectiveMonthlyRent - monthlyMortgage - operatingExpenses;
    const annualCashFlow = monthlyCashFlow * 12;
    const annualNOI = (effectiveMonthlyRent - operatingExpenses) * 12;
    const capRate = inputs.purchasePrice > 0 ? (annualNOI / inputs.purchasePrice) * 100 : 0;
    const cashOnCashReturn = totalCashInvested > 0 ? (annualCashFlow / totalCashInvested) * 100 : 0;
    const grossYield = inputs.purchasePrice > 0 ? ((inputs.monthlyRent * 12) / inputs.purchasePrice) * 100 : 0;
    const breakEvenRent =
      inputs.vacancyRatePercent < 100
        ? (monthlyMortgage + operatingExpenses) / (1 - inputs.vacancyRatePercent / 100)
        : 0;
    const meetsOnePercentRule = inputs.purchasePrice > 0 && inputs.monthlyRent / inputs.purchasePrice >= 0.01;

    return {
      downPayment,
      loanAmount,
      closingCosts,
      totalCashInvested,
      monthlyMortgage,
      effectiveMonthlyRent,
      managementFeeMonthly,
      operatingExpenses,
      monthlyCashFlow,
      annualCashFlow,
      annualNOI,
      capRate,
      cashOnCashReturn,
      grossYield,
      breakEvenRent,
      meetsOnePercentRule,
    };
  }, [inputs]);

  const positive = r.monthlyCashFlow >= 0;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="lg:grid lg:grid-cols-5 lg:gap-8 items-start">

        {/* ── LEFT: Input Panels ── */}
        <div className="lg:col-span-2 space-y-5">

          {/* 1 · The Property */}
          <InputCard step={1} title="The Property">
            <NumberInput
              label="Purchase Price"
              value={inputs.purchasePrice}
              onChange={set('purchasePrice')}
              prefix="$"
              tooltip="The total price you'll pay to buy the property."
            />
            <NumberInput
              label="Expected Monthly Rent"
              value={inputs.monthlyRent}
              onChange={set('monthlyRent')}
              prefix="$"
              tooltip="How much you'll charge tenants per month. Check Zillow or Rentometer for local comparables."
            />
            <NumberInput
              label="Vacancy Rate"
              value={inputs.vacancyRatePercent}
              onChange={set('vacancyRatePercent')}
              suffix="%"
              step={0.5}
              max={100}
              tooltip="The percentage of the year the property sits empty between tenants. 5% equals roughly 18 days per year — a realistic average."
            />
          </InputCard>

          {/* 2 · Your Loan */}
          <InputCard step={2} title="Your Loan">
            <NumberInput
              label="Down Payment"
              value={inputs.downPaymentPercent}
              onChange={set('downPaymentPercent')}
              suffix="%"
              step={1}
              max={100}
              tooltip="Investment properties typically require 20–25% down. Putting less than 20% usually triggers PMI (extra monthly cost)."
              hint={`= ${fmt(r.downPayment)}`}
            />
            <NumberInput
              label="Interest Rate"
              value={inputs.interestRate}
              onChange={set('interestRate')}
              suffix="%"
              step={0.125}
              tooltip="Your annual mortgage interest rate. Rates for investment properties are typically 0.5–1% higher than primary home rates. Check with your lender."
            />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Loan Term</label>
              <select
                value={inputs.loanTermYears}
                onChange={(e) => set('loanTermYears')(Number(e.target.value))}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 text-sm bg-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
              >
                <option value={30}>30 years</option>
                <option value={20}>20 years</option>
                <option value={15}>15 years</option>
                <option value={10}>10 years</option>
              </select>
            </div>
            <NumberInput
              label="Closing Costs"
              value={inputs.closingCostsPercent}
              onChange={set('closingCostsPercent')}
              suffix="%"
              step={0.25}
              max={15}
              tooltip="Fees to finalize the purchase: appraisal, title insurance, origination fees, recording fees, etc. Typically 2–5% of the purchase price."
              hint={`= ${fmt(r.closingCosts)}`}
            />
          </InputCard>

          {/* 3 · Monthly Expenses */}
          <InputCard step={3} title="Monthly Expenses">
            <NumberInput
              label="Property Taxes"
              value={inputs.propertyTaxMonthly}
              onChange={set('propertyTaxMonthly')}
              prefix="$"
              tooltip="Your annual property tax divided by 12. Find the current tax bill on your county assessor's website."
            />
            <NumberInput
              label="Landlord Insurance"
              value={inputs.insuranceMonthly}
              onChange={set('insuranceMonthly')}
              prefix="$"
              tooltip="Rental property (landlord) insurance — different from standard homeowner's insurance. Typically $100–$200/month. Get a quote from your insurer."
            />
            <NumberInput
              label="Repairs & Maintenance"
              value={inputs.maintenanceMonthly}
              onChange={set('maintenanceMonthly')}
              prefix="$"
              tooltip="Budget for ongoing repairs, appliance replacements, and upkeep. A common rule of thumb: 1% of property value per year (e.g., $2,500/yr = $208/mo on a $250K property)."
            />
            <NumberInput
              label="HOA Fee"
              value={inputs.hoaMonthly}
              onChange={set('hoaMonthly')}
              prefix="$"
              tooltip="Monthly homeowners association fee, if any. Enter 0 if not applicable."
            />
            <NumberInput
              label="Property Management"
              value={inputs.managementFeePercent}
              onChange={set('managementFeePercent')}
              suffix="%"
              step={0.5}
              max={25}
              tooltip="If you hire a property manager, they typically charge 8–12% of monthly rent. Enter 0 if you plan to self-manage."
              hint={inputs.managementFeePercent > 0 ? `= ${fmt(r.managementFeeMonthly)}/mo` : undefined}
            />
            <NumberInput
              label="Other Monthly Costs"
              value={inputs.otherMonthly}
              onChange={set('otherMonthly')}
              prefix="$"
              tooltip="Anything else: lawn care, pest control, utilities you cover, trash removal, etc."
            />
          </InputCard>

          <button
            type="button"
            onClick={() => setInputs(DEFAULTS)}
            className="w-full text-sm text-gray-500 hover:text-gray-700 py-2 underline underline-offset-2 transition-colors"
          >
            Reset to defaults
          </button>
        </div>

        {/* ── RIGHT: Results ── */}
        <div className="lg:col-span-3 mt-8 lg:mt-0 space-y-5">

          {/* Hero: Monthly Cash Flow */}
          <div
            className={`rounded-2xl border-2 p-7 ${
              positive
                ? 'bg-emerald-50 border-emerald-200'
                : 'bg-red-50 border-red-200'
            }`}
          >
            <p className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-1">
              Monthly Cash Flow
            </p>
            <p
              className={`text-6xl font-extrabold tracking-tight mb-3 ${
                positive ? 'text-emerald-600' : 'text-red-600'
              }`}
            >
              {fmt(r.monthlyCashFlow)}
            </p>
            <p className="text-gray-700 text-sm leading-relaxed">
              {positive
                ? `This property would put ${fmt(r.monthlyCashFlow)} in your pocket every month after all costs.`
                : `This property would cost you ${fmt(Math.abs(r.monthlyCashFlow))} out of pocket every month.`}
            </p>
            {!positive && (
              <p className="mt-2 text-xs text-red-700">
                To break even you&apos;d need to charge at least{' '}
                <strong>{fmt(r.breakEvenRent)}/month</strong> in rent.
              </p>
            )}
            {positive && (
              <div className="mt-3 flex items-center gap-2">
                <span
                  className={`text-xs font-semibold px-2 py-1 rounded-full ${
                    r.meetsOnePercentRule
                      ? 'bg-emerald-200 text-emerald-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}
                >
                  {r.meetsOnePercentRule ? '✓ Meets the 1% rule' : '✗ Below the 1% rule'}
                </span>
              </div>
            )}
          </div>

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 gap-4">
            <MetricCard
              label="Annual Cash Flow"
              value={fmt(r.annualCashFlow)}
              sub="Per year, after all costs"
              color={r.annualCashFlow >= 0 ? 'emerald' : 'red'}
            />
            <MetricCard
              label="Cash-on-Cash Return"
              value={fmtPct(r.cashOnCashReturn)}
              sub={`On ${fmt(r.totalCashInvested)} invested`}
              color={r.cashOnCashReturn >= 0 ? (r.cashOnCashReturn >= 8 ? 'emerald' : 'amber') : 'red'}
              tooltip="Annual cash flow ÷ total cash you put in (down payment + closing costs). Think of it like the interest rate your down payment earns you."
            />
            <MetricCard
              label="Cap Rate"
              value={fmtPct(r.capRate)}
              sub="Property return, no mortgage"
              color={r.capRate >= 6 ? 'emerald' : r.capRate >= 4 ? 'amber' : 'red'}
              tooltip="How much the property earns as a percentage of its price — ignoring your financing. 5–8% is considered solid for most residential markets."
            />
            <MetricCard
              label="Gross Rental Yield"
              value={fmtPct(r.grossYield)}
              sub="Annual rent ÷ purchase price"
              color="neutral"
              tooltip="Annual rent divided by the purchase price. The '1% rule' means a monthly rent of ≥1% of the price — shown here as a ≥12% gross yield."
            />
          </div>

          {/* Expense Breakdown */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <h3 className="text-base font-semibold text-gray-900 mb-4">
              Where Does The Money Go Each Month?
            </h3>
            <div className="space-y-2.5 text-sm">
              <Row label="Rent collected" amount={r.effectiveMonthlyRent} positive />
              {inputs.vacancyRatePercent > 0 && (
                <Row
                  label={`Vacancy allowance (${inputs.vacancyRatePercent}%)`}
                  amount={-(inputs.monthlyRent - r.effectiveMonthlyRent)}
                />
              )}
              <div className="border-t border-gray-100 my-1" />
              <Row label="Mortgage payment (P+I)" amount={-r.monthlyMortgage} />
              <Row label="Property taxes" amount={-inputs.propertyTaxMonthly} />
              <Row label="Insurance" amount={-inputs.insuranceMonthly} />
              <Row label="Repairs & maintenance" amount={-inputs.maintenanceMonthly} />
              {inputs.hoaMonthly > 0 && <Row label="HOA fee" amount={-inputs.hoaMonthly} />}
              {inputs.managementFeePercent > 0 && (
                <Row label="Property management" amount={-r.managementFeeMonthly} />
              )}
              {inputs.otherMonthly > 0 && <Row label="Other expenses" amount={-inputs.otherMonthly} />}
              <div className="border-t-2 border-gray-200 pt-3 mt-1">
                <div className="flex justify-between items-center font-semibold text-base">
                  <span>Monthly Cash Flow</span>
                  <span className={positive ? 'text-emerald-600' : 'text-red-600'}>
                    {fmt(r.monthlyCashFlow)}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Investment Summary */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <h3 className="text-base font-semibold text-gray-900 mb-4">Your Total Investment</h3>
            <div className="grid grid-cols-2 gap-x-8 gap-y-4 text-sm">
              <SummaryItem label="Loan Amount" value={fmt(r.loanAmount)} />
              <SummaryItem label="Monthly Mortgage" value={fmt(r.monthlyMortgage)} />
              <SummaryItem label="Down Payment" value={fmt(r.downPayment)} />
              <SummaryItem label="Closing Costs" value={fmt(r.closingCosts)} />
              <SummaryItem label="Cash Needed to Close" value={fmt(r.totalCashInvested)} bold />
              <SummaryItem
                label="Break-Even Rent"
                value={`${fmt(r.breakEvenRent)}/mo`}
                bold
              />
            </div>
          </div>

          {/* Ad Unit */}
          <AdUnit size="rectangle" />
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function InputCard({
  step,
  title,
  children,
}: {
  step: number;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
      <h2 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <span className="bg-blue-100 text-blue-600 rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold shrink-0">
          {step}
        </span>
        {title}
      </h2>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

type Color = 'emerald' | 'red' | 'amber' | 'neutral';

const COLOR_MAP: Record<Color, string> = {
  emerald: 'text-emerald-600',
  red: 'text-red-600',
  amber: 'text-amber-600',
  neutral: 'text-gray-900',
};

function MetricCard({
  label,
  value,
  sub,
  color,
  tooltip,
}: {
  label: string;
  value: string;
  sub: string;
  color: Color;
  tooltip?: string;
}) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
      <div className="flex items-start justify-between mb-1">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">{label}</p>
        {tooltip && (
          <div className="ml-1 shrink-0">
            {/* inline tooltip for metric cards */}
            <span
              title={tooltip}
              className="w-4 h-4 rounded-full bg-gray-100 text-gray-400 text-xs font-bold flex items-center justify-center cursor-help"
            >
              ?
            </span>
          </div>
        )}
      </div>
      <p className={`text-2xl font-bold ${COLOR_MAP[color]}`}>{value}</p>
      <p className="text-xs text-gray-500 mt-1">{sub}</p>
    </div>
  );
}

function Row({ label, amount, positive }: { label: string; amount: number; positive?: boolean }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-gray-600">{label}</span>
      <span className={positive ? 'font-semibold text-gray-900' : 'text-gray-700'}>
        {amount >= 0 ? '+' : ''}
        {fmt(amount)}
      </span>
    </div>
  );
}

function SummaryItem({
  label,
  value,
  bold,
}: {
  label: string;
  value: string;
  bold?: boolean;
}) {
  return (
    <div>
      <p className="text-gray-500 text-xs">{label}</p>
      <p className={`${bold ? 'text-base font-bold' : 'font-semibold'} text-gray-900`}>{value}</p>
    </div>
  );
}
