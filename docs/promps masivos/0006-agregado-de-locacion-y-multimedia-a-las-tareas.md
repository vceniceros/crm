## Patrón de diseño obligatorio para abstracciones reutilizables

Las funcionalidades de:

- subida de multimedia
- manejo de ubicación

deben implementarse utilizando **Facade + Strategy**.

### Regla general

No duplicar lógica en componentes ni servicios específicos de tareas.

Toda la complejidad debe quedar encapsulada detrás de fachadas reutilizables.

---

### A. Multimedia → Facade + Strategy

Implementar:

#### Facade
`MediaUploadFacade`

Responsabilidad:
- exponer una API simple para subida de archivos
- decidir estrategia según tipo de archivo
- delegar validación, almacenamiento y generación de URL

Ejemplo de uso esperado:
- `mediaUploadFacade.upload(files, context: 'task')`

#### Strategy

Definir estrategias según tipo de archivo:

- `ImageUploadStrategy`
- `VideoUploadStrategy`

Cada estrategia debe encargarse de:
- validación de tipo MIME/extensión
- carpeta destino:
  - imágenes → `public/images/task`
  - videos → `public/videos/task`
- naming del archivo
- reglas específicas (ej: tamaño máximo)

#### Factory (simple)
Resolver estrategia en base a tipo de archivo:
- no usar `if` distribuidos en el código
- centralizar en la fachada o en una factory interna

---

### B. Ubicación → Facade (+ Strategy opcional)

Implementar:

#### Facade
`LocationFacade`

Responsabilidad:
- encapsular lógica de:
  - selección desde mapa (Leaflet)
  - construcción de objeto de ubicación
  - generación de URL navegable (Maps)
- proveer API simple al resto del sistema

Ejemplo de uso:
- `locationFacade.createFromMapSelection(...)`
- `locationFacade.buildNavigationUrl(location)`

#### Strategy (opcional, solo si aporta claridad)

Separar comportamiento variable si aplica:
- `NavigationUrlStrategy` (Google Maps, etc.)
- no sobreingenierizar si no es necesario

---

### Restricciones

- No permitir que componentes Angular accedan directamente a lógica de subida o construcción de URLs
- No duplicar lógica existente de depósito o clientes: abstraer y reutilizar
- Las fachadas deben ser reutilizables por otros módulos del CRM (no solo tareas)

### Implementación obligatoria

La subida de multimedia debe utilizar `MediaUploadFacade`.

El frontend no debe:
- decidir rutas
- validar tipos manualmente
- construir URLs

Todo eso debe delegarse a la fachada.

El componente solo:
- selecciona archivos
- llama a la fachada
- recibe URLs resultantes
- las asocia al comentario

### Implementación obligatoria

La lógica de ubicación debe centralizarse en `LocationFacade`.

El frontend no debe:
- construir URLs de Maps manualmente
- duplicar lógica de cliente
- manejar coordenadas de forma aislada

Debe:

- reutilizar la selección de ubicación existente (Leaflet)
- delegar en la fachada la construcción del objeto de ubicación
- delegar en la fachada la generación de link navegable

El componente solo:
- muestra ubicación
- invoca navegación

## Requisito adicional de arquitectura

Indicar explícitamente en la entrega:

1. dónde se implementó `MediaUploadFacade`
2. qué estrategias se definieron
3. cómo se resuelve la selección de strategy
4. dónde se implementó `LocationFacade`
5. qué partes del código existente fueron reutilizadas vs duplicadas

No quiero solo código funcionando: quiero ver que las abstracciones quedaron correctamente aplicadas.