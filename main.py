from __future__ import annotations

from pathlib import Path
from queue import Empty, Queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from scanner import ScanConfig, run_scan


class FileReviewScannerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("FileReviewScanner")
        self.root.geometry("900x620")

        self.scan_thread: threading.Thread | None = None
        self.events: Queue[dict] = Queue()
        self.scan_running = False

        self.scan_root_var = tk.StringVar()
        self.output_file_var = tk.StringVar()
        self.filter_mode_var = tk.StringVar(value="all")
        self.extensions_var = tk.StringVar()
        self.duplicates_var = tk.BooleanVar(value=True)

        self.phase_var = tk.StringVar(value="Idle")
        self.files_scanned_var = tk.StringVar(value="0")
        self.files_hashed_var = tk.StringVar(value="0")
        self.duplicate_groups_var = tk.StringVar(value="0")
        self.errors_var = tk.StringVar(value="0")

        self._build_ui()
        self.root.after(200, self._poll_events)

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Scan Root Folder").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.scan_root_var, width=90).grid(row=1, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(frame, text="Browse...", command=self._pick_scan_root).grid(row=1, column=1)

        ttk.Label(frame, text="Output Excel File (.xlsx)").grid(row=2, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(frame, textvariable=self.output_file_var, width=90).grid(row=3, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(frame, text="Browse...", command=self._pick_output_file).grid(row=3, column=1)

        mode_box = ttk.LabelFrame(frame, text="File Type Filtering", padding=10)
        mode_box.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(14, 0))

        ttk.Radiobutton(mode_box, text="Scan all file types", value="all", variable=self.filter_mode_var).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(mode_box, text="Include only selected extensions", value="include", variable=self.filter_mode_var).grid(row=1, column=0, sticky="w")
        ttk.Radiobutton(mode_box, text="Exclude selected extensions", value="exclude", variable=self.filter_mode_var).grid(row=2, column=0, sticky="w")
        ttk.Label(mode_box, text="Extensions (comma/semicolon/space separated):").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(mode_box, textvariable=self.extensions_var, width=90).grid(row=4, column=0, sticky="ew")

        ttk.Checkbutton(frame, text="Identify exact duplicates using SHA-256 hashes", variable=self.duplicates_var).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(12, 0)
        )

        self.start_button = ttk.Button(frame, text="Start Scan", command=self._start_scan)
        self.start_button.grid(row=6, column=0, sticky="w", pady=(14, 0))

        status = ttk.LabelFrame(frame, text="Status / Progress", padding=10)
        status.grid(row=7, column=0, columnspan=2, sticky="nsew", pady=(16, 0))

        rows = [
            ("Current Phase", self.phase_var),
            ("Files Scanned", self.files_scanned_var),
            ("Files Hashed", self.files_hashed_var),
            ("Duplicate Groups Found", self.duplicate_groups_var),
            ("Errors Encountered", self.errors_var),
        ]
        for i, (label, var) in enumerate(rows):
            ttk.Label(status, text=label + ":", font=("Segoe UI", 10, "bold")).grid(row=i, column=0, sticky="w", padx=(0, 12), pady=2)
            ttk.Label(status, textvariable=var).grid(row=i, column=1, sticky="w", pady=2)

        self.status_text = tk.Text(status, height=12, wrap=tk.WORD)
        self.status_text.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        self.status_text.insert(tk.END, "Ready.\n")
        self.status_text.configure(state=tk.DISABLED)

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(7, weight=1)
        status.columnconfigure(1, weight=1)
        status.rowconfigure(6, weight=1)

    def _append_status(self, message: str) -> None:
        self.status_text.configure(state=tk.NORMAL)
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.configure(state=tk.DISABLED)

    def _pick_scan_root(self) -> None:
        p = filedialog.askdirectory(title="Select Root Folder to Scan")
        if p:
            self.scan_root_var.set(p)

    def _pick_output_file(self) -> None:
        p = filedialog.asksaveasfilename(
            title="Select Output Excel Workbook",
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
            initialfile="FileReviewScanner_Report.xlsx",
        )
        if p:
            self.output_file_var.set(p)

    def _start_scan(self) -> None:
        if self.scan_running:
            messagebox.showwarning("Scan Running", "A scan is already running. Please wait for it to finish.")
            return

        scan_root = Path(self.scan_root_var.get().strip())
        output_file = Path(self.output_file_var.get().strip())
        mode = self.filter_mode_var.get().strip()

        if not scan_root.exists() or not scan_root.is_dir():
            messagebox.showerror("Invalid Root", "Please select a valid root folder to scan.")
            return
        if not output_file.parent.exists():
            messagebox.showerror("Invalid Output", "Output folder does not exist.")
            return
        if output_file.suffix.lower() != ".xlsx":
            messagebox.showerror("Invalid Output", "Output file must end with .xlsx")
            return
        if mode in {"include", "exclude"} and not self.extensions_var.get().strip():
            messagebox.showerror("Extensions Required", "Please enter at least one extension for include/exclude mode.")
            return

        self.scan_running = True
        self.start_button.configure(state=tk.DISABLED)
        self._append_status(f"Starting scan for: {scan_root}")

        config = ScanConfig(
            root_path=scan_root,
            output_file=output_file,
            filter_mode=mode,
            extension_text=self.extensions_var.get(),
            detect_duplicates=self.duplicates_var.get(),
        )

        self.scan_thread = threading.Thread(target=run_scan, args=(config, self.events), daemon=True)
        self.scan_thread.start()

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                etype = event.get("type")
                if etype == "progress":
                    self.phase_var.set(event.get("phase", self.phase_var.get()))
                    self.files_scanned_var.set(str(event.get("files_scanned", self.files_scanned_var.get())))
                    self.files_hashed_var.set(str(event.get("files_hashed", self.files_hashed_var.get())))
                    self.duplicate_groups_var.set(str(event.get("duplicate_groups", self.duplicate_groups_var.get())))
                    self.errors_var.set(str(event.get("errors", self.errors_var.get())))
                    if msg := event.get("message"):
                        self._append_status(msg)
                elif etype == "done":
                    self.scan_running = False
                    self.start_button.configure(state=tk.NORMAL)
                    out = event.get("output_file", "")
                    self._append_status(f"Completed. Report saved to: {out}")
                    messagebox.showinfo("Scan Complete", f"Scan completed successfully.\n\nReport: {out}")
                elif etype == "error":
                    self.scan_running = False
                    self.start_button.configure(state=tk.NORMAL)
                    err = event.get("message", "Unknown error")
                    self._append_status(f"ERROR: {err}")
                    messagebox.showerror("Scan Failed", err)
        except Empty:
            pass
        finally:
            self.root.after(200, self._poll_events)


def main() -> None:
    root = tk.Tk()
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    app = FileReviewScannerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
