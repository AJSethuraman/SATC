// Dynamic line items + live total calculation for the invoice form.
(function () {
  "use strict";

  const body = document.getElementById("items-body");
  const addBtn = document.getElementById("add-item");
  const form = document.getElementById("invoice-form");
  if (!body || !form) return;

  const symbols = {
    USD: "$", EUR: "€", GBP: "£", JPY: "¥", CAD: "$", AUD: "$", INR: "₹",
    CHF: "CHF ", CNY: "¥", BRL: "R$", ZAR: "R", MXN: "$", SGD: "$", NZD: "$"
  };

  function currencySymbol() {
    const sel = document.getElementById("currency");
    return symbols[sel ? sel.value : "USD"] || "";
  }

  function fmt(n) {
    return currencySymbol() + Number(n || 0).toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  }

  function num(el) {
    const v = parseFloat(el && el.value);
    return isNaN(v) ? 0 : v;
  }

  function rowTemplate() {
    const tr = document.createElement("tr");
    tr.className = "item-row";
    tr.innerHTML =
      '<td><input type="text" name="item_description" placeholder="Item or service"></td>' +
      '<td><input type="number" name="item_quantity" class="qty" step="any" min="0" value="1"></td>' +
      '<td><input type="number" name="item_rate" class="rate" step="any" min="0" value="0"></td>' +
      '<td class="col-amount row-amount">0.00</td>' +
      '<td class="col-actions"><button type="button" class="btn-remove" title="Remove">&times;</button></td>';
    return tr;
  }

  function recalc() {
    let subtotal = 0;
    body.querySelectorAll(".item-row").forEach(function (row) {
      const qty = num(row.querySelector(".qty"));
      const rate = num(row.querySelector(".rate"));
      const amount = qty * rate;
      subtotal += amount;
      row.querySelector(".row-amount").textContent = fmt(amount);
    });

    const discountVal = num(document.getElementById("discount_value"));
    const discountPct = document.getElementById("discount_is_percent").value === "percent";
    const discount = discountPct ? subtotal * discountVal / 100 : discountVal;

    const taxableBase = subtotal - discount;
    const taxVal = num(document.getElementById("tax_value"));
    const taxPct = document.getElementById("tax_is_percent").value === "percent";
    const tax = taxPct ? taxableBase * taxVal / 100 : taxVal;

    const shipping = num(document.getElementById("shipping"));
    const total = taxableBase + tax + shipping;
    const paid = num(document.getElementById("amount_paid"));
    const balance = total - paid;

    document.getElementById("t-subtotal").textContent = fmt(subtotal);
    document.getElementById("t-discount").textContent = "-" + fmt(discount);
    document.getElementById("t-tax").textContent = fmt(tax);
    document.getElementById("t-total").textContent = fmt(total);
    document.getElementById("t-balance").textContent = fmt(balance);
  }

  addBtn.addEventListener("click", function () {
    body.appendChild(rowTemplate());
    recalc();
  });

  body.addEventListener("click", function (e) {
    if (e.target.classList.contains("btn-remove")) {
      const rows = body.querySelectorAll(".item-row");
      if (rows.length > 1) {
        e.target.closest(".item-row").remove();
      } else {
        // Keep at least one row; just clear it.
        const row = e.target.closest(".item-row");
        row.querySelectorAll("input").forEach(function (i) {
          i.value = i.classList.contains("qty") ? "1" : (i.classList.contains("rate") ? "0" : "");
        });
      }
      recalc();
    }
  });

  // Recalculate on any input change.
  document.addEventListener("input", recalc);
  document.addEventListener("change", recalc);

  // Lightweight required-field validation before submit.
  form.addEventListener("submit", function (e) {
    const required = [
      ["from_info", "From / business information"],
      ["bill_to", "Bill To / client information"],
      ["invoice_number", "Invoice number"]
    ];
    const missing = [];
    required.forEach(function (pair) {
      const el = form.querySelector('[name="' + pair[0] + '"]');
      if (el && !el.value.trim()) missing.push(pair[1]);
    });
    let hasItem = false;
    body.querySelectorAll(".item-row").forEach(function (row) {
      const desc = row.querySelector('[name="item_description"]').value.trim();
      const rate = num(row.querySelector(".rate"));
      if (desc || rate) hasItem = true;
    });
    if (!hasItem) missing.push("at least one line item");

    if (missing.length) {
      e.preventDefault();
      alert("Please complete the following before saving:\n- " + missing.join("\n- "));
    }
  });

  recalc();
})();
