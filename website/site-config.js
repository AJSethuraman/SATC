/* ============================================================================
   SATC_CONFIG — THE ONLY THING YOU NEED TO EDIT
   ----------------------------------------------------------------------------
   Loaded by BOTH index.html and privacy.html. It lives in its own file so the
   contact address has one home — when it was inline in index.html, the privacy
   page carried a second hard-coded copy that would silently go stale and send
   deletion requests to a dead mailbox.

   1) WHERE THE FORM GOES (do this first — it's the whole point of the page):
      Sign up free at https://formspree.io, create a form, and paste its ID
      below as `formspreeId` (it looks like "xkgwabcd" — the last part of the
      URL Formspree gives you). Submissions then land in your inbox.
      Leave it blank and the form falls back to opening the visitor's email
      app with everything pre-filled — it works, but far fewer people finish.
   2) CONTACT: set your email (and optionally phone / location / LinkedIn).
      Leave a field as "" to hide it automatically.
   3) OPTIONAL — BOOKING: paste a Calendly or Cal.com link and a "book a phone
      call" button appears on the CONFIRMATION screen, after the form is sent
      — never beside it, where it would be a way to skip the questions.
      Point it at a PHONE CALL event type only; in-person meetings are not
      self-scheduled. Booking is optional for the visitor either way — we say
      we'll be in touch regardless. Leave blank to hide it entirely.
   ============================================================================ */

  // Assigned onto window deliberately: intake.js is a separate file and reads
  // this through window.SATC_CONFIG. A top-level `const` would be lexically
  // scoped to this script and invisible to it — the inline IIFEs below would
  // still work, so the breakage would only show up at submit time.
  window.SATC_CONFIG = {
    contact: {
      email:      "arjun_sethuraman@satcllp.com",
      phone:      "",                     // e.g. "+1 (305) 555-0140" — blank = hidden
      location:   "By appointment · Remote &amp; in&#8209;person",
      linkedin:   "",                     // e.g. "https://www.linkedin.com/in/your-handle"
      formspreeId: "mwleqelj"             // Formspree form ID — submissions email to the address above
    },
    // ── Optional: a "book a time" link beside the form ──────────────
    booking: {
      // Phone-call event type only — in-person meetings are not self-scheduled.
      // Shown on the CONFIRMATION screen after the form is sent, never beside
      // it. Blank = the button disappears and we just say we'll be in touch.
      // NOTE: this is the event's URL slug, which Calendly keeps separate from
      // its display name — renaming the event does NOT update this link, but
      // editing the link under "event link" does, and would break it here.
      url: "https://calendly.com/arjun_sethuraman-satcllp/new-meeting"
    },
    // ── Analytics (optional, off by default) ───────────────────────
    // provider "plausible" + domain, OR "cloudflare" + token, OR "ga" + id
    analytics: { provider: "", domain: "", token: "", id: "" }
  };
