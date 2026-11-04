import { api } from '@/api/qdc'

/** Piece by piece through the app (DEC-330): without a Drive the piece is the whole file. */
export async function caricaAPezzi(
  allegato: number,
  file: File,
  pezzo: number,
  avanzamento: (percentuale: number) => void,
): Promise<void> {
  for (let inizio = 0; inizio < file.size; inizio += pezzo) {
    await api.pezzoAllegatoVerbale(allegato, inizio, file.slice(inizio, inizio + pezzo))
    avanzamento(Math.round((Math.min(inizio + pezzo, file.size) / file.size) * 100))
  }
}

export function misura(byte: number): string {
  if (byte >= 1024 ** 3) return `${(byte / 1024 ** 3).toFixed(1).replace('.', ',')} GB`
  if (byte >= 1024 ** 2) return `${Math.ceil(byte / 1024 ** 2)} MB`
  return `${Math.ceil(byte / 1024)} KB`
}
