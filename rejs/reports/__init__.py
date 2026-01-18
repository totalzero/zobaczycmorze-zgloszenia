from django.http import HttpResponse
from django.utils.timezone import now
from .builder import RaportRejsuBuilder
from .excel import ExcelExporter


def generate_rejs_report(rejs, user):
	builder = RaportRejsuBuilder(rejs, user)

	# ---------- NAZWA PLIKU ----------
	filename = f"raport_rejsu_{rejs.nazwa}_{now().strftime('%Y-%m-%d')}.xlsx"

	# ---------- BUILDER ----------
	zaloga = builder.build_zaloga()
	wachty = builder.build_wachty()
	wplaty = builder.build_wplaty()
	dane_wrazliwe = builder.build_dane_wrazliwe()
	crew_list = builder.build_crew_list()

	# ---------- EXCEL ----------
	# filename nie jest potrzebny, bo zapisujemy do HttpResponse
	exporter = ExcelExporter(filename=None)

	if zaloga:
		exporter.add_zaloga(zaloga)

	if wachty:
		exporter.add_wachty(wachty)

	if wplaty:
		exporter.add_wplaty(wplaty)

	if dane_wrazliwe:
		exporter.add_dane_wrazliwe(dane_wrazliwe)

	if crew_list:
		exporter.add_crew_list(crew_list)

	# ---------- RESPONSE ----------
	response = HttpResponse(
		content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
	)
	response["Content-Disposition"] = f'attachment; filename="{filename}"'

	exporter.wb.save(response)
	return response
