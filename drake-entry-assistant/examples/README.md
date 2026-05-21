# Examples

This folder contains synthetic demo assets and instructions for reproducible local testing.

## No Real Client Data

- Use demo-only values.
- Do not store real taxpayer records here.
- Do not commit real SSNs/EINs.

## Generate Sample Workbook

From `drake-entry-assistant/`:

```bash
python -c "from dea.demo import create_sample_workbook; create_sample_workbook('examples/sample_intake.xlsx')"
```

The generated workbook includes required tabs and columns for the loader:

- `Clients`
- `W2s`

## Schema Notes

`Clients` requires the headers from `dea.excel_loader.REQUIRED_CLIENT_COLUMNS`.

`W2s` requires the headers from `dea.excel_loader.REQUIRED_W2_COLUMNS`.

The sample generator writes one valid synthetic client and one valid synthetic W-2 for CLI demos and tests.
