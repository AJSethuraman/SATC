/* Address autocomplete — free, no API key.
 *
 * Type-ahead address suggestions powered by Photon (https://photon.komoot.io),
 * an open geocoder built on OpenStreetMap data. Runs entirely in the visitor's
 * browser, so it needs no server config or key. If the service is slow or
 * unreachable, the field degrades gracefully to a normal text box.
 *
 * Usage: add `data-address-autocomplete` to an <input>/<textarea>. Options:
 *   data-ac-target="<id>"  write the picked address into another element
 *   data-ac-mode="append"  append (newline-separated) instead of replacing
 */
(function () {
  var css =
    ".ac-wrap{position:relative;}" +
    ".ac-list{position:absolute;left:0;right:0;top:100%;z-index:60;background:#fff;" +
    "border:1px solid var(--gray-200,#e2e8f0);border-radius:8px;margin-top:4px;" +
    "box-shadow:0 10px 20px -6px rgba(15,23,41,.12),0 4px 6px -1px rgba(15,23,41,.08);" +
    "max-height:260px;overflow-y:auto;padding:4px;}" +
    ".ac-item{padding:8px 10px;border-radius:6px;font-size:14px;color:#334155;" +
    "cursor:pointer;line-height:1.4;}" +
    ".ac-item:hover,.ac-item.ac-active{background:var(--brand-50,#eff4ff);color:var(--brand,#2563eb);}";
  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  function pick(p, key) { return p[key]; }

  function cityOf(p) {
    return pick(p, "city") || pick(p, "town") || pick(p, "village") ||
           pick(p, "municipality") || pick(p, "county") || "";
  }

  function isUS(c) {
    return c === "United States" || c === "United States of America" || c === "USA";
  }

  function formatLines(p) {
    var lines = [];
    var l1 = [p.housenumber, p.street].filter(Boolean).join(" ") || p.name || "";
    if (l1) lines.push(l1);
    var l2 = [cityOf(p), p.state].filter(Boolean).join(", ");
    if (p.postcode) l2 = l2 ? l2 + " " + p.postcode : p.postcode;
    if (l2) lines.push(l2);
    if (p.country && !isUS(p.country)) lines.push(p.country);
    return lines.join("\n");
  }

  function oneLine(p) {
    var head = [p.housenumber, p.street].filter(Boolean).join(" ") || p.name;
    return [head, cityOf(p), p.state, p.postcode, p.country]
      .filter(Boolean).join(", ");
  }

  function attach(input) {
    var targetId = input.getAttribute("data-ac-target");
    var target = targetId ? document.getElementById(targetId) : input;
    if (!target) target = input;
    var mode = input.getAttribute("data-ac-mode") || "replace";

    var wrap = document.createElement("div");
    wrap.className = "ac-wrap";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    var list = document.createElement("div");
    list.className = "ac-list";
    list.style.display = "none";
    wrap.appendChild(list);

    var items = [];
    var activeIdx = -1;
    var timer = null;

    function close() {
      list.style.display = "none";
      list.innerHTML = "";
      items = [];
      activeIdx = -1;
    }

    function setActive(i) {
      var nodes = list.querySelectorAll(".ac-item");
      for (var k = 0; k < nodes.length; k++) {
        nodes[k].classList.toggle("ac-active", k === i);
      }
      activeIdx = i;
    }

    function choose(p) {
      var formatted = formatLines(p);
      if (target === input || mode === "replace") {
        target.value = formatted;
      } else {
        var cur = (target.value || "").replace(/\s+$/, "");
        target.value = cur ? cur + "\n" + formatted : formatted;
      }
      if (target !== input) input.value = "";
      target.dispatchEvent(new Event("input", { bubbles: true }));
      close();
    }

    function render(feats) {
      list.innerHTML = "";
      items = feats || [];
      if (!items.length) { close(); return; }
      items.forEach(function (f) {
        var div = document.createElement("div");
        div.className = "ac-item";
        div.textContent = oneLine(f.properties);
        div.addEventListener("mousedown", function (e) {
          e.preventDefault();
          choose(f.properties);
        });
        list.appendChild(div);
      });
      list.style.display = "block";
      activeIdx = -1;
    }

    function search(q) {
      fetch("https://photon.komoot.io/api/?limit=5&q=" + encodeURIComponent(q))
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (input.value.trim() === q) render(d.features || []);
        })
        .catch(function () { /* unreachable: leave as a plain text field */ });
    }

    input.setAttribute("autocomplete", "off");
    input.addEventListener("input", function () {
      var q = input.value.trim();
      if (q.length < 4) { close(); return; }
      clearTimeout(timer);
      timer = setTimeout(function () { search(q); }, 300);
    });

    input.addEventListener("keydown", function (e) {
      if (list.style.display === "none") return;
      var n = list.querySelectorAll(".ac-item").length;
      if (e.key === "ArrowDown") { e.preventDefault(); setActive(Math.min(activeIdx + 1, n - 1)); }
      else if (e.key === "ArrowUp") { e.preventDefault(); setActive(Math.max(activeIdx - 1, 0)); }
      else if (e.key === "Enter") {
        // While the list is open, Enter picks the highlighted suggestion (or
        // just closes the list) — never let it submit the surrounding form.
        e.preventDefault();
        if (activeIdx >= 0) choose(items[activeIdx].properties);
        else close();
      }
      else if (e.key === "Escape") { close(); }
    });

    document.addEventListener("click", function (e) {
      if (!wrap.contains(e.target)) close();
    });
  }

  function init() {
    var els = document.querySelectorAll("[data-address-autocomplete]");
    for (var i = 0; i < els.length; i++) attach(els[i]);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
