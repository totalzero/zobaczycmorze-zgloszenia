from django.http import HttpResponse
from django.utils.timezone import now

from .builder import RaportRejsuBuilder
from .excel import ExcelExporter


def generate_rejs_report(rejs, user):
	builder = RaportRejsuBuilder(rejs, user)

	filename = f"raport_rejsu_{rejs.nazwa}_{now().date()}.xlsx"
	exporter = ExcelExporter(filename)

	zaloga = builder.build_zaloga()
	wachty = builder.build_wachty()
	wplaty = builder.build_wplaty()
	dane_wrazliwe = builder.build_dane_wrazliwe()

	exporter.add_zaloga(zaloga)
	exporter.add_wachty(wachty)
	exporter.add_wplaty(wplaty)
	exporter.add_dane_wrazliwe(dane_wrazliwe)

	response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
	response["Content-Disposition"] = f'attachment; filename="{filename}"'

	exporter.wb.save(response)
	return response
