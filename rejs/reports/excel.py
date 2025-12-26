from openpyxl import Workbook
from openpyxl.styles import Font


class ExcelExporter:
    def __init__(self, filename):
        self.wb = Workbook()
        self.filename = filename

    def save(self):
        self.wb.save(self.filename)

    # ---------- ZAŁOGA ----------
    def add_zaloga(self, rows):
        ws = self.wb.active
        ws.title = "Załoga"

        headers = rows[0].keys() if rows else []
        ws.append(list(headers))

        for cell in ws[1]:
            cell.font = Font(bold=True)

        for r in rows:
            ws.append(list(r.values()))

    # ---------- WACHTY ----------
    def add_wachty(self, wachty):
        ws = self.wb.create_sheet("Wachty")

        for w in wachty:
            ws.append([f"Wachta: {w['nazwa']}"])
            ws.append(["Imię", "Nazwisko", "Rola"])
            for c in w["czlonkowie"]:
                ws.append([c["imie"], c["nazwisko"], c["rola"]])
            ws.append([])

    # ---------- WPŁATY ----------
    def add_wplaty(self, rows):
        ws = self.wb.create_sheet("Wpłaty")

        headers = rows[0].keys() if rows else []
        ws.append(list(headers))

        for cell in ws[1]:
            cell.font = Font(bold=True)

        for r in rows:
            ws.append(list(r.values()))

    # ---------- DANE WRAŻLIWE ----------
    def add_dane_wrazliwe(self, rows):
        if not rows:
            return

        ws = self.wb.create_sheet("Dane wrażliwe")

        headers = rows[0].keys()
        ws.append(list(headers))

        for cell in ws[1]:
            cell.font = Font(bold=True)

        for r in rows:
            ws.append(list(r.values()))
