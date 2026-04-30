# Explicación del Código - Tracker Gym

Bueno, voy a explicar cómo está armado todo, bastante sencillo en realidad.

## La Estructura General

Todo el código está en un único archivo HTML. Tiene tres partes principales: HTML (la estructura), CSS (los estilos), y JavaScript (lógica que hay detrás).

## Almacenamiento de Datos

Lo primero es que los datos se guardan en `localStorage`. Básicamente es un lugar en el navegador donde podés guardar información en tu dispositivo. Cuando cierrás la aplicación y la vuelves a abrir, ahí siguen los datos. (De vez en cuando sería recomendable descargar el .csv por si acaso)

El array `ejercicios` tiene los 22 ejercicios del inicio, cada uno con esta estructura:

```javascript
{
  id: 1,
  grupo: "Pecho",
  nombre: "Press de Banca",
  descripcion: "Acostado con barra",
  imagen: "data:image/svg+xml,...",
  pesoNormal: 60,
  pesoMax: 100,
  notas: "Espalda plana"
}
```

Cada propiedad es lo que te imaginás: el `id` es único para cada ejercicio, el `grupo` es para filtrar (Pecho, Espalda, etc), y los pesos son números que el usuario (YO) puede editar.

## Las Funciones - Lo Importante

Cuando arranca la aplicación, llama a `cargarDelLocal()`. Esta función simplemente va a buscar si hay algo guardado en localStorage. Si hay, carga los ejercicios guardados. Si no hay nada, usa los 22 que vienen por defecto.

```javascript
function cargarDelLocal() {
  let datos = localStorage.getItem('ejercicios');
  if (datos) {
    ejercicios = JSON.parse(datos);
  }
}
```

Después llama a `mostrarEjercicios()` que hace:

1. Mira qué grupo seleccionaste en el desplegable (dropdown)
2. Filtra los ejercicios según ese grupo (o muestra todos si seleccionaste "Todos")
3. Genera el HTML para cada ejercicio usando template literals
4. Lo pone en la pantalla

Es literalmente recorrer el array y generar HTML con cada dato.

Cuando editas un peso, llama a `actualizarPeso(id, campo, valor)`. Busca el ejercicio por ID, cambia el peso (puede ser normal o máximo), y guarda todo en localStorage con `guardarEnLocal()`.

```javascript
function actualizarPeso(id, campo, valor) {
  let ejercicio = ejercicios.find(e => e.id === id);
  if (ejercicio) {
    ejercicio[campo] = valor;
    guardarEnLocal();
  }
}
```

`guardarEnLocal()` simplemente convierte el array a JSON y lo guarda en localStorage:

```javascript
function guardarEnLocal() {
  localStorage.setItem('ejercicios', JSON.stringify(ejercicios));
}
```

## Para Agregar y Editar

Cuando hacess click en "Nuevo Ejercicio", llama a `abrirModalNuevo()`. Esto limpia el formulario y muestra el modal.

Cuando haces click en "Editar", llama a `abrirModalEditar(id)`. Busca el ejercicio por ID, completa los campos del formulario con los datos actuales, y muestra el modal.

Cuando guardas, `guardarNuevoEjercicio()` revisa si estás creando algo nuevo o editando algo existente. Si `editandoId` es 0, crea un nuevo ejercicio con un ID único. Si es mayor a 0, actualiza el ejercicio que estaba editando.

```javascript
function guardarNuevoEjercicio() {
  let editandoId = document.getElementById('editandoId').value;
  
  if (editandoId == 0) {
    // Crear nuevo
    let nuevoId = Math.max(...ejercicios.map(e => e.id)) + 1;
    let nuevoEjercicio = {
      id: nuevoId,
      grupo: ...,
      nombre: ...,
      // etc
    };
    ejercicios.push(nuevoEjercicio);
  } else {
    // Editar existente
    let ejercicio = ejercicios.find(e => e.id == editandoId);
    Object.assign(ejercicio, { ...nuevosdatos });
  }
  
  guardarEnLocal();
  cerrarModal();
  mostrarEjercicios();
}
```

Después guarda todo en localStorage, cierra el modal, y recarga la vista.

## Eliminar Ejercicios

`eliminarEjercicio(id)` hace exactamente lo que suena. Pide confirmación (para que no borres algo sin querer), elimina el ejercicio del array usando `filter()`, guarda en localStorage, y recarga la vista:

```javascript
function eliminarEjercicio(id) {
  if (confirm('¿Eliminar este ejercicio?')) {
    ejercicios = ejercicios.filter(e => e.id !== id);
    guardarEnLocal();
    mostrarEjercicios();
  }
}
```

## Filtrar por Grupo Muscular

Cuando cambias el dropdown, llama a `mostrarEjercicios()` de nuevo. Adentro de esa función:

```javascript
let grupo = document.getElementById('grupoSelect').value;
let filtrados = grupo === 'Todos' 
  ? ejercicios 
  : ejercicios.filter(e => e.grupo === grupo);
```

Agarra el valor del dropdown. Si es "Todos", muestra todos. Si es un grupo específico, filtra solo los ejercicios de ese grupo.

## Notas en los Ejercicios

Cuando escribis una nota, llama a `actualizarNotas(id, valor)`. Busca el ejercicio y actualiza el campo notas:

```javascript
function actualizarNotas(id, valor) {
  let ejercicio = ejercicios.find(e => e.id === id);
  if (ejercicio) {
    ejercicio.notas = valor;
    guardarEnLocal();
  }
}
```

## Estadísticas

`actualizarEstadisticas()` calcula tres números:
- Total de ejercicios (siempre 22, o los que tengas)
- Cuántos grupos musculares hay
- Cuántos ejercicios se ven en pantalla (según el filtro)

Usa `Set` para contar grupos únicos sin repetidos, y filtra para contar cuántos se ven:

```javascript
function actualizarEstadisticas() {
  let grupo = document.getElementById('grupoSelect').value;
  let filtrados = grupo === 'Todos' 
    ? ejercicios 
    : ejercicios.filter(e => e.grupo === grupo);
  
  // Muestra los números en los elementos de stats
}
```

## Descargar en CSV

`descargarDatos()` genera un archivo CSV con todos los ejercicios. Básicamente arma un string con los datos separados por comas, crea un blob (no sabía que era esto y es un bloque en ram ), y lo descarga:

```javascript
function descargarDatos() {
  let csv = 'ID,Grupo,Nombre,Descripción,Peso Normal,Peso Máximo,Notas\n';
  ejercicios.forEach(e => {
    csv += `${e.id},"${e.grupo}","${e.nombre}",...\n`;
  });
  
  let blob = new Blob([csv], { type: 'text/csv' });
  let url = window.URL.createObjectURL(blob);
  let a = document.createElement('a');
  a.href = url;
  a.download = 'ejercicios.csv';
  a.click();
}
```

Básicamente crear un archivo de texto y que el navegador lo descargue.

## El CSS (Es un poco cutre)

Las media queries usan breakpoints:
- Más de 1200px: PC, 3 columnas
- 768px a 1200px: Tablet, 2 columnas
- Menos de 768px: Móvil, 1 columna 

```css
@media (max-width: 1200px) {
  .content {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .content {
    grid-template-columns: 1fr;
  }
}
```

## Imágenes

Las imágenes son data URLs en SVG (por los pixeles). Básicamente es código que genera una imagen directamente sin necesidad de un archivo. Si por algún motivo falla (que probablemente falle), hay un placeholder que muestra un SVG genérico de "Ejercicio".

## Event Listeners

Al final del código, hay dos event listeners principales:

1. `window.addEventListener('load', ...)` - Cuando carga la página, carga los datos, muestra los ejercicios y actualiza las estadísticas.

2. `document.getElementById('grupoSelect').addEventListener('change', ...)` - Cuando cambias el dropdown, recarga los ejercicios y estadísticas.

Basicamente eso es todo. El flujo es:

1. Cargar datos guardados (o usar los por defecto)
2. Mostrar ejercicios
3. Usuario interactúa (edita, agrega, elimina)
4. Guardar cambios en localStorage
5. Recarga la vista

Se repite lo mismo una y otra vez. No hay nada complicado, es un CRUD básico (Create, Read, Update, Delete) pero en el navegador y guardando en localStorage.

---

Eso es básicamente todo lo que hay. El código no es complicado, es bastante directo. Usa funciones simples, arrays, objetos, un poco de DOM manipulation con JavaScript. Puro HTML, CSS y JS.


