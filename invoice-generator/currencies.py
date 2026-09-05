"""ISO 4217 currency table: symbols, English names, and **minor units**.

``helpers.py`` knows 14 currencies and formats every one of them with exactly
two decimal places. That is wrong for about a quarter of the world's money and
it is wrong in the direction that costs someone real money:

* **Zero-decimal currencies.** The yen has no sub-unit. ``format_money(1500,
  "JPY")`` renders ``¥1,500.00``, which reads to a Japanese client as an
  invoice for one *hundred and fifty thousand* yen presented with a stray
  separator — and ``stripe_utils.py:100`` does ``int(round(amount * 100))``
  for every currency, so a ¥1,500 invoice really is charged as ¥150,000.
  A 100x overcharge, silently, with no error anywhere.
* **Three-decimal currencies.** The Kuwaiti dinar divides into 1,000 fils.
  KWD 1.500 truncated to two places is KWD 1.50, and sent to Stripe as
  ``150`` when it should be ``1500`` — a 10x *under*charge.

So ``decimals`` here is not decoration. It is the number every display and
every gateway conversion has to consult before it touches an amount.

This module is **additive**: it does not modify ``helpers.py`` and does not
change what any existing caller does today. The 14 codes helpers already
knows carry exactly helpers' symbols, character for character, so a page that
switches from ``currency_symbol`` to ``symbol_for`` renders identically.
``tests/test_currencies.py`` holds that agreement as a guard.

Sources and conventions:

* Minor units follow **ISO 4217**, not any payment processor's table. Where a
  processor disagrees the ISO value stays and the divergence is noted inline
  (see HUF, MGA, TWD) — a processor's quirk belongs in the code that talks to
  that processor, not in the currency's definition.
* Where a currency has no distinct glyph in common use, **the symbol is the
  code itself**. An invented or borrowed glyph is worse than no glyph: "$" on
  a Sudanese pound invoice is a claim about which currency is owed.
* Fund codes (CLF, USN, XDR, ...), precious metals (XAU, XAG, ...) and the
  testing codes (XTS, XXX) are deliberately absent. None of them is money you
  can invoice someone in, and CLF's four decimals would be the only entry
  outside {0, 2, 3}.
* Withdrawn codes are absent too (SLL, MRO, STD, CUC, ZWL, ...). Billing in a
  currency that no longer exists is not a feature.
"""
import math

# (code, English name, symbol, minor-unit digits)
#
# Alphabetical by code. Every non-2 value carries the reason it is not 2, and
# every entry whose minor unit could not be confirmed against ISO 4217 with
# confidence is marked UNVERIFIED rather than quietly asserted.
_TABLE = (
    ("AED", "UAE Dirham", "د.إ", 2),
    ("AFN", "Afghan Afghani", "؋", 2),
    ("ALL", "Albanian Lek", "L", 2),
    ("AMD", "Armenian Dram", "֏", 2),
    # ANG is being replaced by XCG (Caribbean guilder) from 2025; both are
    # listed while the changeover runs.
    ("ANG", "Netherlands Antillean Guilder", "ƒ", 2),
    ("AOA", "Angolan Kwanza", "Kz", 2),
    ("ARS", "Argentine Peso", "$", 2),
    ("AUD", "Australian Dollar", "$", 2),
    ("AWG", "Aruban Florin", "ƒ", 2),
    ("AZN", "Azerbaijani Manat", "₼", 2),
    ("BAM", "Bosnia-Herzegovina Convertible Mark", "KM", 2),
    ("BBD", "Barbadian Dollar", "$", 2),
    ("BDT", "Bangladeshi Taka", "৳", 2),
    ("BGN", "Bulgarian Lev", "лв", 2),
    ("BHD", "Bahraini Dinar", "BD", 3),  # 1,000 fils
    ("BIF", "Burundian Franc", "FBu", 0),  # no sub-unit in use
    ("BMD", "Bermudian Dollar", "$", 2),
    ("BND", "Brunei Dollar", "$", 2),
    ("BOB", "Bolivian Boliviano", "Bs", 2),
    ("BRL", "Brazilian Real", "R$", 2),
    ("BSD", "Bahamian Dollar", "$", 2),
    ("BTN", "Bhutanese Ngultrum", "Nu.", 2),
    ("BWP", "Botswana Pula", "P", 2),
    ("BYN", "Belarusian Ruble", "Br", 2),
    ("BZD", "Belize Dollar", "$", 2),
    ("CAD", "Canadian Dollar", "$", 2),
    ("CDF", "Congolese Franc", "FC", 2),
    # "CHF " keeps helpers.CURRENCY_SYMBOLS' trailing space so the rendered
    # string stays "CHF 1,250.00" and not "CHF1,250.00". The space is part of
    # the existing contract, not a typo; CURRENCY_CHOICES strips it for the
    # dropdown label only.
    ("CHF", "Swiss Franc", "CHF ", 2),
    ("CLP", "Chilean Peso", "$", 0),  # centavos withdrawn
    ("CNY", "Chinese Yuan Renminbi", "¥", 2),
    ("COP", "Colombian Peso", "$", 2),
    ("CRC", "Costa Rican Colon", "₡", 2),
    ("CUP", "Cuban Peso", "$", 2),
    ("CVE", "Cape Verdean Escudo", "$", 2),
    ("CZK", "Czech Koruna", "Kč", 2),
    ("DJF", "Djiboutian Franc", "Fdj", 0),  # no sub-unit in use
    ("DKK", "Danish Krone", "kr", 2),
    ("DOP", "Dominican Peso", "RD$", 2),
    ("DZD", "Algerian Dinar", "DA", 2),
    ("EGP", "Egyptian Pound", "E£", 2),
    ("ERN", "Eritrean Nakfa", "Nfk", 2),
    ("ETB", "Ethiopian Birr", "Br", 2),
    ("EUR", "Euro", "€", 2),
    ("FJD", "Fijian Dollar", "$", 2),
    ("FKP", "Falkland Islands Pound", "£", 2),
    ("GBP", "Pound Sterling", "£", 2),
    ("GEL", "Georgian Lari", "₾", 2),
    ("GHS", "Ghanaian Cedi", "₵", 2),
    ("GIP", "Gibraltar Pound", "£", 2),
    ("GMD", "Gambian Dalasi", "D", 2),
    ("GNF", "Guinean Franc", "FG", 0),  # no sub-unit in use
    ("GTQ", "Guatemalan Quetzal", "Q", 2),
    ("GYD", "Guyanese Dollar", "$", 2),
    ("HKD", "Hong Kong Dollar", "HK$", 2),
    ("HNL", "Honduran Lempira", "L", 2),
    ("HTG", "Haitian Gourde", "G", 2),
    # HUF is 2 in ISO 4217 (100 fillér, withdrawn from circulation but still
    # the standard's minor unit). Stripe treats HUF as zero-decimal for
    # payouts. ISO wins here; a Stripe adapter must apply its own rule rather
    # than have this table lie to every other caller.
    ("HUF", "Hungarian Forint", "Ft", 2),
    ("IDR", "Indonesian Rupiah", "Rp", 2),
    ("ILS", "Israeli New Shekel", "₪", 2),
    ("INR", "Indian Rupee", "₹", 2),
    ("IQD", "Iraqi Dinar", "IQD", 3),  # 1,000 fils
    ("IRR", "Iranian Rial", "IRR", 2),
    ("ISK", "Icelandic Krona", "kr", 0),  # aurar withdrawn 2003
    ("JMD", "Jamaican Dollar", "J$", 2),
    ("JOD", "Jordanian Dinar", "JD", 3),  # 1,000 fils
    ("JPY", "Japanese Yen", "¥", 0),  # no sub-unit
    ("KES", "Kenyan Shilling", "KSh", 2),
    ("KGS", "Kyrgyzstani Som", "som", 2),
    ("KHR", "Cambodian Riel", "៛", 2),
    ("KMF", "Comorian Franc", "CF", 0),  # no sub-unit in use
    ("KPW", "North Korean Won", "₩", 2),
    ("KRW", "South Korean Won", "₩", 0),  # jeon withdrawn
    ("KWD", "Kuwaiti Dinar", "KD", 3),  # 1,000 fils
    ("KYD", "Cayman Islands Dollar", "$", 2),
    ("KZT", "Kazakhstani Tenge", "₸", 2),
    ("LAK", "Lao Kip", "₭", 2),
    ("LBP", "Lebanese Pound", "L£", 2),
    ("LKR", "Sri Lankan Rupee", "Rs", 2),
    ("LRD", "Liberian Dollar", "$", 2),
    ("LSL", "Lesotho Loti", "L", 2),
    ("LYD", "Libyan Dinar", "LD", 3),  # 1,000 dirham
    ("MAD", "Moroccan Dirham", "MAD", 2),
    ("MDL", "Moldovan Leu", "L", 2),
    # MGA divides into 5 iraimbilanja, which is not a power of ten; ISO 4217
    # records 2 digits for it. Stripe treats MGA as zero-decimal. ISO value
    # kept, divergence noted — same call as HUF.
    ("MGA", "Malagasy Ariary", "Ar", 2),
    ("MKD", "Macedonian Denar", "ден", 2),
    ("MMK", "Myanmar Kyat", "K", 2),
    ("MNT", "Mongolian Tugrik", "₮", 2),
    ("MOP", "Macanese Pataca", "MOP$", 2),
    # MRU divides into 5 khoums; as with MGA, ISO 4217 records 2 digits.
    ("MRU", "Mauritanian Ouguiya", "UM", 2),
    ("MUR", "Mauritian Rupee", "₨", 2),
    ("MVR", "Maldivian Rufiyaa", "Rf", 2),
    ("MWK", "Malawian Kwacha", "MK", 2),
    ("MXN", "Mexican Peso", "$", 2),
    ("MYR", "Malaysian Ringgit", "RM", 2),
    ("MZN", "Mozambican Metical", "MT", 2),
    ("NAD", "Namibian Dollar", "$", 2),
    ("NGN", "Nigerian Naira", "₦", 2),
    ("NIO", "Nicaraguan Cordoba", "C$", 2),
    ("NOK", "Norwegian Krone", "kr", 2),
    ("NPR", "Nepalese Rupee", "Rs", 2),
    ("NZD", "New Zealand Dollar", "$", 2),
    ("OMR", "Omani Rial", "OMR", 3),  # 1,000 baisa
    ("PAB", "Panamanian Balboa", "B/.", 2),
    ("PEN", "Peruvian Sol", "S/", 2),
    ("PGK", "Papua New Guinean Kina", "K", 2),
    ("PHP", "Philippine Peso", "₱", 2),
    ("PKR", "Pakistani Rupee", "₨", 2),
    ("PLN", "Polish Zloty", "zł", 2),
    ("PYG", "Paraguayan Guarani", "₲", 0),  # centimos withdrawn
    ("QAR", "Qatari Riyal", "QR", 2),
    ("RON", "Romanian Leu", "lei", 2),
    ("RSD", "Serbian Dinar", "дин", 2),
    ("RUB", "Russian Ruble", "₽", 2),
    ("RWF", "Rwandan Franc", "FRw", 0),  # no sub-unit in use
    ("SAR", "Saudi Riyal", "SR", 2),
    ("SBD", "Solomon Islands Dollar", "$", 2),
    ("SCR", "Seychellois Rupee", "₨", 2),
    ("SDG", "Sudanese Pound", "SDG", 2),
    ("SEK", "Swedish Krona", "kr", 2),
    ("SGD", "Singapore Dollar", "$", 2),
    ("SHP", "Saint Helena Pound", "£", 2),
    ("SLE", "Sierra Leonean Leone", "Le", 2),  # 2022 redenomination of SLL
    ("SOS", "Somali Shilling", "Sh", 2),
    ("SRD", "Surinamese Dollar", "$", 2),
    ("SSP", "South Sudanese Pound", "SSP", 2),
    ("STN", "Sao Tome and Principe Dobra", "Db", 2),
    ("SVC", "Salvadoran Colon", "₡", 2),
    ("SYP", "Syrian Pound", "SYP", 2),
    ("SZL", "Swazi Lilangeni", "E", 2),
    ("THB", "Thai Baht", "฿", 2),
    ("TJS", "Tajikistani Somoni", "SM", 2),
    ("TMT", "Turkmenistani Manat", "m", 2),
    ("TND", "Tunisian Dinar", "DT", 3),  # 1,000 millimes
    ("TOP", "Tongan Pa'anga", "T$", 2),
    ("TRY", "Turkish Lira", "₺", 2),
    ("TTD", "Trinidad and Tobago Dollar", "TT$", 2),
    # TWD is 2 in ISO 4217; Stripe requires whole-dollar amounts for it. Same
    # call as HUF and MGA: the standard's value lives here.
    ("TWD", "New Taiwan Dollar", "NT$", 2),
    ("TZS", "Tanzanian Shilling", "TSh", 2),
    ("UAH", "Ukrainian Hryvnia", "₴", 2),
    ("UGX", "Ugandan Shilling", "USh", 0),  # cents withdrawn
    ("USD", "US Dollar", "$", 2),
    ("UYU", "Uruguayan Peso", "$U", 2),
    ("UZS", "Uzbekistani Som", "so'm", 2),
    # VED is the 2021 redenomination; VES remains in the standard alongside it
    # while the changeover runs. UNVERIFIED: VED's minor unit is recorded here
    # as 2 by analogy with VES rather than from a confirmed reading of the ISO
    # amendment. Confirm before invoicing in it.
    ("VED", "Venezuelan Bolivar (2021 redenomination)", "Bs.", 2),
    ("VES", "Venezuelan Bolivar Soberano", "Bs.S", 2),
    ("VND", "Vietnamese Dong", "₫", 0),  # hao/xu withdrawn
    ("VUV", "Vanuatu Vatu", "VT", 0),  # no sub-unit
    ("WST", "Samoan Tala", "WS$", 2),
    ("XAF", "Central African CFA Franc", "FCFA", 0),  # no sub-unit in use
    ("XCD", "East Caribbean Dollar", "$", 2),
    # XCG replaces ANG from 2025. UNVERIFIED: 2 digits is the expected value
    # for a 1:1 successor to the Antillean guilder, but this code is new
    # enough that it has not been confirmed against a published ISO table.
    ("XCG", "Caribbean Guilder", "Cg", 2),
    ("XOF", "West African CFA Franc", "CFA", 0),  # no sub-unit in use
    ("XPF", "CFP Franc", "₣", 0),  # no sub-unit
    ("YER", "Yemeni Rial", "YER", 2),
    ("ZAR", "South African Rand", "R", 2),
    ("ZMW", "Zambian Kwacha", "ZK", 2),
    # UNVERIFIED: ZWG (Zimbabwe Gold, introduced 2024) is recorded here as 2
    # digits, which matches how it is quoted, but the currency is new and
    # unstable enough that the figure has not been confirmed against a
    # published ISO table. Confirm before invoicing in it.
    ("ZWG", "Zimbabwe Gold", "ZiG", 2),
)

#: ``{"USD": {"code": ..., "name": ..., "symbol": ..., "decimals": ...}, ...}``
CURRENCIES = {
    code: {"code": code, "name": name, "symbol": symbol, "decimals": decimals}
    for code, name, symbol, decimals in _TABLE
}

# The currencies a small practice actually bills in, in the order a human
# would look for them. Everything else follows alphabetically. This is a
# display convenience only — nothing about pricing or rounding reads it.
_PREFERRED = ("USD", "EUR", "GBP", "CAD", "AUD", "JPY", "INR", "CHF", "CNY")

#: Minor units assumed for a code this table has never heard of. Two is the
#: overwhelming majority and matches what ``helpers.format_money`` already
#: does, so an unknown code degrades to today's behaviour rather than to a
#: different wrong answer.
DEFAULT_DECIMALS = 2


def _normalise(code):
    """Return ``code`` as a bare uppercase string; ``""`` for None/blank."""
    return str(code or "").strip().upper()


def get_currency(code):
    """Return the entry for ``code``, or **None** if it is unknown.

    Deliberately does *not* fall back to USD. A caller that asks about "ZWG"
    and is handed the US dollar will format a Zimbabwean invoice with "$" and
    two decimals and never learn that it got a different currency than the one
    it asked for — the same class of silent substitution that
    ``helpers.parse_money`` refuses for amounts. None means "I don't know";
    what to do about that is the caller's decision, not this table's.

    The returned dict is a copy: the table is module-level state shared by
    every request in the process, and one caller mutating an entry would
    change the symbol on everybody else's invoices.
    """
    entry = CURRENCIES.get(_normalise(code))
    return dict(entry) if entry is not None else None


def symbol_for(code):
    """Return the display symbol for ``code``.

    An unknown code returns **the uppercased code itself** ("ZZZ" -> "ZZZ"), so
    an unrecognised currency shows up on the invoice as a visible, searchable
    string instead of being rendered with a borrowed glyph or with nothing at
    all. ``helpers.currency_symbol`` returns "" in that case, which is how an
    invoice can read "1,250.00" with no indication of what it is denominated
    in; that is the behaviour this replaces for new callers.

    None or blank returns "" — there is no code to show.
    """
    code = _normalise(code)
    if not code:
        return ""
    entry = CURRENCIES.get(code)
    return entry["symbol"] if entry is not None else code


def decimals_for(code):
    """Return the minor-unit digits for ``code``.

    Unknown codes return ``DEFAULT_DECIMALS`` (2). This is the one place a
    default is right rather than dangerous: two decimals is what every caller
    does today, so an unknown code is formatted no worse than it is now, and
    the alternative — refusing to render — would blank an invoice over an
    unrecognised three-letter string. Callers that must not guess should ask
    ``get_currency`` first and act on the None.
    """
    entry = CURRENCIES.get(_normalise(code))
    return entry["decimals"] if entry is not None else DEFAULT_DECIMALS


def format_amount(amount, code="USD"):
    """Format ``amount`` in ``code``, honouring that currency's minor units.

    ``format_amount(1500, "JPY")`` -> ``¥1,500`` (no sub-unit exists)
    ``format_amount(1500, "KWD")`` -> ``KD1,500.000`` (1,000 fils)
    ``format_amount(1500, "USD")`` -> ``$1,500.00``

    Defensive in the same places ``helpers.parse_money`` is, and for the same
    reason: this runs inside a template, and an exception here is a 500 on a
    page the client is looking at, not a caught error.

    * ``None`` and unparseable input format as zero, matching
      ``helpers.format_money``.
    * ``inf``/``nan`` format as zero. A NaN total once reached the History
      KPIs and rendered ``$nan`` for every invoice in the account (see
      ``helpers.parse_money``); the fix belongs at the parse seam, but the
      display seam should not repeat it either.
    * A bool formats as zero rather than as ``$1.00`` — ``True`` is an answer,
      not an amount.
    * The sign goes outside the symbol (``-$5.00``, not ``$-5.00``), and an
      amount that rounds to zero never renders as ``-$0.00``.
    """
    if isinstance(amount, bool):
        amount = 0.0
    try:
        value = float(amount if amount is not None else 0.0)
    except (TypeError, ValueError):
        value = 0.0
    if not math.isfinite(value):
        value = 0.0

    digits = decimals_for(code)
    magnitude = round(abs(value), digits)
    sign = "-" if value < 0 and magnitude != 0 else ""
    return f"{sign}{symbol_for(code)}{magnitude:,.{digits}f}"


def _label(entry):
    # The symbol is stripped for the label only: CHF's stored symbol carries a
    # trailing space so "CHF 1,250.00" reads correctly, and "(CHF )" in a
    # dropdown does not.
    return f"{entry['code']} — {entry['name']} ({entry['symbol'].strip()})"


#: ``[("USD", "USD — US Dollar ($)"), ...]`` for a ``<select>``: the nine
#: currencies this practice actually bills in first, then everything else by
#: code. Built once at import — the table never changes at runtime.
CURRENCY_CHOICES = [
    (code, _label(CURRENCIES[code])) for code in _PREFERRED if code in CURRENCIES
] + [
    (code, _label(CURRENCIES[code]))
    for code in sorted(CURRENCIES)
    if code not in _PREFERRED
]
