"""The FDIC peer monitor: bank-level Call Report figures via FDIC BankFind.

Entity-keyed (one block per bank slot, quarters as rows), keyless live API.
The adapter and this spec are the whole of what is FDIC-specific; everything
else comes from ``credit_suite.engine``.
"""
