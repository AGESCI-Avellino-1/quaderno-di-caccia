"""Using the app as another user, to help them fill something in or to check a problem
(DEC-167).

- the capigruppo and the technical administrators who are also capi in BuonaStrada may
  act as anyone with an account; the staff of a unit as its ragazzi and their parents
  (`policy.puo_impersonare`); never a capo still waiting for BuonaStrada, never nested;
- a reason is required; it ends with "Torna a te" or by itself after 30 minutes;
- everything is allowed but the account and the person's own choices (password, email,
  passkeys, devices, what parents see, emails, rights, consents): `middleware.BLOCCATE`;
- the person sees in their account who used the app in their place, when and why; the
  Co.Ca. sees the whole list;
- the audit log keeps the real user as the author of every change (the middleware runs
  after auditlog's), the access log names both.
"""

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import ModelloTracciato

DURATA = timedelta(minutes=30)


class ImpersonazioneQuerySet(models.QuerySet):
    def in_corso(self, adesso=None):
        return self.filter(finita_il__isnull=True, scade_il__gt=adesso or timezone.now())


class Impersonazione(ModelloTracciato):
    impersonatore = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Kept when the account goes (erasure): the person still knows who it was.
    nome_impersonatore = models.CharField(max_length=200)
    impersonato = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="impersonazioni"
    )
    motivo = models.CharField(max_length=300)
    scade_il = models.DateTimeField()
    finita_il = models.DateTimeField(null=True, blank=True)

    objects = ImpersonazioneQuerySet.as_manager()

    class Meta:
        verbose_name = "uso dell'app al posto di un altro"
        verbose_name_plural = "usi dell'app al posto di un altro"
        ordering = ["-creato_il"]

    def __str__(self) -> str:
        return f"{self.nome_impersonatore} al posto di {self.impersonato}"

    @property
    def fine(self):
        return self.finita_il or self.scade_il

    def termina(self) -> None:
        if self.finita_il is None:
            self.finita_il = min(timezone.now(), self.scade_il)
            self.save(update_fields=["finita_il", "aggiornato_il"])
