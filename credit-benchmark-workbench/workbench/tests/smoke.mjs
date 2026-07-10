// SSR + interaction smoke test for the Workbench artifact.
import { JSDOM } from "jsdom";

const dom = new JSDOM("<!doctype html><html><body><div id='root'></div></body></html>", {
  url: "http://localhost/", pretendToBeVisual: true,
});
global.window = dom.window;
global.document = dom.window.document;
Object.defineProperty(global, "navigator", { value: dom.window.navigator, configurable: true });
global.HTMLElement = dom.window.HTMLElement;
global.Blob = dom.window.Blob;
global.URL = dom.window.URL;

const React = (await import("react")).default;
const { createRoot } = await import("react-dom/client");
const { act } = await import("react");
const Workbench = (await import("./compiled.js")).default;

global.IS_REACT_ACT_ENVIRONMENT = true;

const root = createRoot(document.getElementById("root"));
await act(async () => {
  root.render(React.createElement(Workbench));
});

const body = document.body;
const text = () => body.textContent;

let failures = [];
function check(name, cond) {
  if (cond) console.log("PASS", name);
  else { console.log("FAIL", name); failures.push(name); }
}

// 1. Initial render: banner, sample borrower, flags
check("renders title", text().includes("Commercial Credit Benchmark Workbench"));
check("synthetic banner shown", text().includes("SYNTHETIC DEMONSTRATION DATA"));
check("sample borrower loaded",
  [...body.querySelectorAll("input")].some((i) => i.value.includes("Meridian Fabrication")));
check("metric cards render", text().includes("Total Debt / EBITDA"));
check("flag chips render", /DEPARTURE|WATCH|SEVERE|IN RANGE/.test(text()));
check("svg distributions render", body.querySelectorAll("svg").length >= 5);
check("no form tags", body.querySelectorAll("form").length === 0);

// sample borrower vs cmm adjusted peers should carry at least one adverse flag
const chips = [...body.querySelectorAll("span")].map((s) => s.textContent);
check("at least one adverse flag on sample",
  chips.some((c) => ["WATCH", "DEPARTURE", "SEVERE"].includes(c)));

// 2. Click first metric card -> detail drawer
const cards = [...body.querySelectorAll("div")].filter(
  (d) => d.getAttribute("title") === "Click for source, basis and methodology");
check("clickable cards exist", cards.length >= 4);
await act(async () => {
  cards[0].dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
});
check("drawer shows basis", text().includes("Fiscal-year basis"));
check("drawer shows sources", text().includes("company-FY"));
check("drawer shows mechanism", text().includes("Mechanism (commercial credit)"));
check("drawer shows raw vs adjusted table", text().includes("Raw public") &&
  text().includes("Adjusted"));
check("drawer shows adjustment note", text().includes("dispersion widened"));
check("drawer shows pre-2020 baseline row", text().includes("pre-2020 baseline"));

// close drawer
const closeBtn = [...body.querySelectorAll("button")].find((b) => b.textContent === "Close");
await act(async () => {
  closeBtn.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
});

// 3. Toggle raw view
const rawBtn = [...body.querySelectorAll("button")].find((b) => b.textContent === "Raw public");
await act(async () => {
  rawBtn.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
});
check("raw view active", text().includes("grading vs. raw"));

// back to adjusted
const adjBtn = [...body.querySelectorAll("button")].find(
  (b) => b.textContent === "Private-MM adjusted");
await act(async () => {
  adjBtn.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
});

// 4. Export memo
const memoBtn = [...body.querySelectorAll("button")].find(
  (b) => b.textContent === "Export memo");
await act(async () => {
  memoBtn.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
});
const memo = body.querySelector("pre") ? body.querySelector("pre").textContent : "";
check("memo opens", memo.includes("# Benchmark review memo"));
check("memo has data caveat", memo.includes("DATA CAVEAT"));
check("memo has position table", memo.includes("| Metric | Borrower |"));
check("memo has findings", memo.includes("## Findings (departure vs. normalization)"));
check("memo has coverage gaps section", memo.includes("## Coverage gaps"));
check("memo has methodology appendix", memo.includes("## Methodology appendix"));
check("memo has basis labels", memo.includes("Basis"));
check("memo has adjustment disclosure", memo.includes("dispersion widened"));
check("memo has validation stats", memo.includes("hit rate"));
check("memo has refresh instructions", memo.includes("ccbw"));
check("memo frames trajectory", /Structural departure|Normalizing|Persistent|Single period/.test(memo));

// 5. Sanity: numbers in memo match inputs (leverage 162/32 = 5.06x)
check("memo leverage matches hand calc", memo.includes("5.06x"));
// EBITDA margin 32/240 = 13.3%
check("memo margin matches hand calc", memo.includes("13.3%"));

// 6. Segment switch exercises every segment without crashing
for (const segLabel of ["CRE Operating Companies", "Healthcare", "Agribusiness", "Leveraged"]) {
  const btn = [...body.querySelectorAll("button")].find((b) =>
    b.textContent.startsWith(segLabel.split(" ")[0]));
  if (btn) {
    await act(async () => {
      btn.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
    });
  }
  check(`segment switch: ${segLabel}`, text().length > 1000);
}

console.log(failures.length ? `\n${failures.length} FAILURES` : "\nALL CHECKS PASSED");
process.exit(failures.length ? 1 : 0);
