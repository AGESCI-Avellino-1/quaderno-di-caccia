/**
 * Receipt photos (DEC-86) travel as a data URL inside the JSON body, so a movement
 * recorded offline waits in the queue with its photo, encrypted like the rest. Photos
 * are scaled down first (a phone shot is several MB); PDFs go as they are. The server
 * checks the kind of file again.
 */

const LATO_MASSIMO = 1600
const QUALITA = 0.8
export const DIMENSIONE_MASSIMA = 10 * 1024 * 1024

function comeDataUrl(file: Blob): Promise<string> {
  return new Promise((risolvi, rifiuta) => {
    const lettore = new FileReader()
    lettore.onload = () => risolvi(String(lettore.result))
    lettore.onerror = () => rifiuta(lettore.error)
    lettore.readAsDataURL(file)
  })
}

async function ridimensiona(file: File): Promise<string | null> {
  if (typeof createImageBitmap !== 'function') return null
  try {
    const immagine = await createImageBitmap(file)
    const scala = Math.min(1, LATO_MASSIMO / Math.max(immagine.width, immagine.height))
    const tela = document.createElement('canvas')
    tela.width = Math.round(immagine.width * scala)
    tela.height = Math.round(immagine.height * scala)
    const contesto = tela.getContext('2d')
    if (!contesto) return null
    contesto.drawImage(immagine, 0, 0, tela.width, tela.height)
    return tela.toDataURL('image/jpeg', QUALITA)
  } catch {
    return null
  }
}

/** The file as a data URL, a photo scaled down to 1600 px; throws a readable error. */
export async function leggiGiustificativo(file: File): Promise<string> {
  if (file.type.startsWith('image/')) {
    const piccola = await ridimensiona(file)
    if (piccola) return piccola
  }
  if (file.size > DIMENSIONE_MASSIMA) throw new Error('Il file è troppo grande: al massimo 10 MB.')
  return comeDataUrl(file)
}
