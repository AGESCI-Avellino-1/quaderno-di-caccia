// Push notifications (DEC-345), imported by the service worker that vite-plugin-pwa generates.
// The text was checked on the server: nothing personal, it shows on a locked phone.
self.addEventListener('push', (evento) => {
  if (!evento.data) return
  let dati
  try {
    dati = evento.data.json()
  } catch {
    return
  }
  evento.waitUntil(
    self.registration.showNotification(dati.titolo, {
      body: dati.testo || undefined,
      icon: '/icons/icon-192.png',
      badge: '/icons/icon-192.png',
      data: { percorso: dati.percorso || '/' },
    }),
  )
})

self.addEventListener('notificationclick', (evento) => {
  evento.notification.close()
  // Always within the app: only the path comes with the notification.
  const destinazione = new URL(evento.notification.data?.percorso || '/', self.location.origin)
  if (destinazione.origin !== self.location.origin) return
  evento.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((aperte) => {
      const aperta = aperte.find((c) => 'focus' in c)
      if (!aperta) return self.clients.openWindow(destinazione.href)
      // The app goes there itself (pwa/aperturaNotifica.ts): navigate() fails on a window this
      // worker does not control, e.g. after an update, and on some iPhones.
      const percorso = destinazione.pathname + destinazione.search + destinazione.hash
      aperta.postMessage({ tipo: 'qdc-apri', percorso })
      return aperta.focus()
    }),
  )
})
