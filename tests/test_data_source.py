from occam_template_desk.core.data_source import OccamWorkbook


def test_client_data_loads_from_sample_excel_workbook():
    wb = OccamWorkbook("occam_template_desk/sample_data/Occam_Data.xlsx")
    clients = wb.clients()
    assert len(clients) >= 5
    assert clients[0]["Client ID"] == "C-1001"


def test_client_selection_returns_correct_row():
    wb = OccamWorkbook("occam_template_desk/sample_data/Occam_Data.xlsx")
    client = wb.get_client_by_id("C-1003")
    assert client["Client Name"] == "Northstar Design Co."
    assert wb.invoices_for_client("C-1003")[0]["Invoice Number"] == "INV-24019"
