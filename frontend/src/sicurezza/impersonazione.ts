/**
 * Using the app as another user (a capo helping a family, see the backend app
 * `impersonazione`). While it lasts nothing is saved on the device and nothing goes
 * through the offline queue: the encrypted copy and the queue belong to the capo, and a
 * queued write sent later would run as the wrong person.
 */
let attiva = false

export function impostaImpersonazione(valore: boolean): void {
  attiva = valore
}

export function inImpersonazione(): boolean {
  return attiva
}
