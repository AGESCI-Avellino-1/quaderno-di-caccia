# Release forms already decided by the secretariat: their files go, as for new ones
# (DEC-200). Dates and outcome stay.

from django.db import migrations


def togli(apps, schema_editor):
    Iscrizione = apps.get_model("buonacaccia", "IscrizioneBuonaCaccia")
    for iscrizione in Iscrizione.objects.exclude(esito_liberatoria=""):
        campi = []
        if iscrizione.liberatoria_firmata:
            iscrizione.liberatoria_firmata.delete(save=False)
            campi.append("liberatoria_firmata")
        if iscrizione.esito_liberatoria == "VALIDATA" and iscrizione.liberatoria_da_firmare:
            iscrizione.liberatoria_da_firmare.delete(save=False)
            campi.append("liberatoria_da_firmare")
        if campi:
            iscrizione.save(update_fields=campi)


class Migration(migrations.Migration):
    dependencies = [("buonacaccia", "0002_piccole_orme")]

    operations = [migrations.RunPython(togli, migrations.RunPython.noop)]
