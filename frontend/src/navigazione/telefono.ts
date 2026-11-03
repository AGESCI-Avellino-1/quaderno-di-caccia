/**
 * The addresses behind the buttons next to a phone number (DEC-301): call, WhatsApp, SMS.
 * Numbers come from BuonaStrada and the forms as typed ("333 123 4567", "+39 333…",
 * "0039…"): WhatsApp wants the international number in digits only, and a number with no
 * international prefix is Italian.
 */
export type PulsanteTelefono = 'chiama' | 'whatsapp' | 'sms'

export const PULSANTI_PREDEFINITI: PulsanteTelefono[] = ['chiama', 'whatsapp']

export function internazionale(numero: string): string {
  const cifre = numero.replace(/[^\d+]/g, '')
  if (cifre.startsWith('+')) return cifre.slice(1).replace(/\D/g, '')
  if (cifre.startsWith('00')) return cifre.slice(2)
  return `39${cifre}`
}

export function indirizziTelefono(numero: string): Record<PulsanteTelefono, string> {
  const piu = `+${internazionale(numero)}`
  return {
    chiama: `tel:${piu}`,
    whatsapp: `https://wa.me/${internazionale(numero)}`,
    sms: `sms:${piu}`,
  }
}
