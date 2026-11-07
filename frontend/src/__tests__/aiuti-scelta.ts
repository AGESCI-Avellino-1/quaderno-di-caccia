import type { DOMWrapper, VueWrapper } from '@vue/test-utils'

/** Chooses in a SceltaDaElenco (DEC-395): writes in the field, then picks the first match. */
export async function scegliPersona(
  pagina: VueWrapper | DOMWrapper<Element>,
  campo: string,
  testo: string,
): Promise<void> {
  const input = pagina.get<HTMLInputElement>(campo)
  await input.trigger('focus')
  await input.setValue(testo)
  await input.trigger('input')
  await input.trigger('keydown', { key: 'Enter' })
}
