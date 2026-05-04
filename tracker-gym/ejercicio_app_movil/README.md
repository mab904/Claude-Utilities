# De HTML a App Móvil - Tracker Gym PWA

Bueno, básicamente tomé el archivo HTML del tracker de ejercicios y lo convertí en una PWA (Progressive Web App). Lo que significa que ahora puedes instalarlo en tu móvil como si fuera una app de verdad.

## Qué es una PWA

Una PWA es una página web que el navegador te deja instalar como si fuera una app nativa. No necesitás subirla a la App Store ni a Google Play. Simplemente la abres desde el móvil, el navegador te pregunta si querés añadirla a la pantalla de inicio, y listo. Aparece con su icono (el icono lo he hecho en el paint en 2 minutos), se abre en pantalla completa.

Para esto, hay tres cosas que necesita cualquier PWA:

1. Un `manifest.json` — le dice al navegador cómo se llama la app, qué colores usar, y qué icono mostrar
2. Un `sw.js` (Service Worker) — es un script que corre en segundo plano y guarda los archivos en caché para que funcione offline
3. Los iconos — en PNG, en dos tamaños (192x192 y 512x512) (hay 2 basicamente porque uno es de la pantalla de inicio y el otro de cuando se abre la app)

## Los Archivos que Se Añadieron

### manifest.json

```json
{
  "name": "Seguimiento de Ejercicios",
  "short_name": "Ejercicios",
  "display": "standalone",
  "background_color": "#000000",
  "theme_color": "#FFD700",
  "icons": [...]
}
```

Importante de aquí es `"display": "standalone"`. Eso es lo que hace que cuando abras la app no se vea la barra del navegador.

El `theme_color` es el color de la barra de estado del móvil (donde está la hora).
### sw.js (Service Worker)

Esto es más interesante. Un Service Worker es un script JavaScript que vive entre tu app y la red. Intercepta todas las peticiones que hace la app y decide si tirarlas a internet o responder desde la caché.

```javascript
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
});
```

Cuando se instala por primera vez, guarda todos los archivos en caché. Después, cada vez que la app pide algo, primero mira si lo tiene guardado. Si lo tiene, lo devuelve desde caché (rápido y sin internet). Si no lo tiene, lo busca en la red.

## Cambios en el index.html

Del HTML original solo hubo que tocar dos cosas.

**En el `<head>`**, se añadieron las etiquetas que le dicen al navegador que esto es una PWA:

```html
<!-- Vincula el manifest -->
<link rel="manifest" href="manifest.json">

<!-- Color de la barra de estado -->
<meta name="theme-color" content="#FFD700">

<!-- Para iOS (Safari es especial) -->
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Ejercicios">
<link rel="apple-touch-icon" href="icon-192.png">
```

Lo de iOS es porque Apple hace las cosas a su manera. Safari no usa el manifest para los iconos ni para el modo standalone, así que hay que decírselo con sus propias meta tags.

**Al final del `<script>`**, se registra el Service Worker:

```javascript
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('./sw.js')
    .then(() => console.log('Service Worker registrado ✓'))
    .catch(err => console.warn('SW error:', err));
}
```

El `if ('serviceWorker' in navigator)` es para que no pete en navegadores viejos que no lo soporten. Si lo soporta, registra el sw.js y a correr.

## Estructura Final de Archivos

```
/
├── index.html       ← El HTML original con los tags PWA añadidos
├── manifest.json    ← Configuración de la app
├── sw.js            ← Service Worker (caché y offline)
├── icon-192.png     ← Icono para pantalla de inicio
└── icon-512.png     ← Icono para splash screen
```

## Despliegue en Netlify

La PWA necesita estar en un servidor HTTPS para funcionar. No vale abrir el HTML directamente desde el explorador de archivos, el Service Worker no se registra en local con `file://`.

Para el despliegue usé Netlify porque tenía que hacer un repositorio aparte en Github para usar el Github Pages y me daba pereza cambiar el orden de mis repositorios.

**La app está desplegada aquí:**

-> [Seguimiento de Ejercicios](https://meek-creponne-56adbd.netlify.app/)

## Cómo Instalarla en el Móvil

**En Android:**
1. Abrir el enlace de arriba desde **Chrome**
2. Menú de los tres puntos (arriba a la derecha) → **"Añadir a pantalla de inicio"**
3. Le das el nombre que quieras y confirmas

Chrome a veces muestra un banner automático abajo preguntando si querés instalarla. Si aparece, puedes usar ese directamente.

**En iPhone (No lo he probado):**
1. Abrir el enlace desde **Safari** (tiene que ser Safari, no Chrome)
2. Botón de compartir (el cuadrado con la flecha) → **"Añadir a pantalla de inicio"**


---

Eso es todo, del HTML original no se tocó para nada en la lógica, que yo recuerde (A lo mejor algún contendor para que se muestre estéticamente bien).
