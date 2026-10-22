"""Import a BuonaStrada "Ricerca Soci" CSV from the command line.

Default is a dry run that prints the preview; pass --applica to write.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.importazione.buonastrada import FormatoNonValido, leggi_ricerca_soci
from apps.importazione.servizi import GruppoNonCorrispondente, anteprima, applica


class Command(BaseCommand):
    help = "Importa l'export 'Ricerca Soci' di BuonaStrada (anteprima, oppure --applica)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("file", type=Path)
        parser.add_argument("--applica", action="store_true", dest="scrivi", help="Scrive i dati.")

    def handle(self, *args, file: Path, scrivi: bool = False, **options) -> None:
        if not file.exists():
            raise CommandError(f"File non trovato: {file}")
        try:
            risultato = leggi_ricerca_soci(file)
            riepilogo = applica(risultato) if scrivi else anteprima(risultato)
        except (FormatoNonValido, GruppoNonCorrispondente) as exc:
            raise CommandError(str(exc)) from exc

        modo = "APPLICATA" if scrivi else "ANTEPRIMA (nessuna modifica salvata)"
        self.stdout.write(self.style.MIGRATE_HEADING(f"Importazione {modo}"))
        for etichetta, valori in (
            ("Persone create", riepilogo.persone_create),
            ("Persone aggiornate", riepilogo.persone_aggiornate),
            ("Genitori creati", riepilogo.genitori_creati),
            ("Unità create", riepilogo.unita_create),
            ("Appartenenze aperte", riepilogo.appartenenze_aperte),
            ("Appartenenze chiuse", riepilogo.appartenenze_chiuse),
        ):
            self.stdout.write(f"{etichetta}: {len(valori)}")
        for differenza in riepilogo.differenze:
            self.stdout.write(
                self.style.WARNING(
                    f"[differenza] {differenza.persona} · {differenza.campo}: "
                    f"app={differenza.valore_app!r} BuonaStrada={differenza.valore_buonastrada!r}"
                    f" — {differenza.motivo}"
                )
            )
        for avviso in riepilogo.avvisi:
            stile = self.style.ERROR if avviso["gravita"] == "errore" else self.style.WARNING
            self.stdout.write(
                stile(f"[{avviso['gravita']}] riga {avviso['riga']}: {avviso['messaggio']}")
            )
