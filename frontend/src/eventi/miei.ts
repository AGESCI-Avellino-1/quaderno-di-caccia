/**
 * Which events are the user's own (DEC-432), told apart only where there are others too. An
 * answer saved before the server said it has no `mio`: all one's own.
 */
export function conAltri(eventi: { mio?: boolean }[]): boolean {
  return eventi.some((e) => e.mio === false) && eventi.some((e) => e.mio !== false)
}
