# Instrucciones del Repositorio para GitHub Copilot y Asistentes de Desarrollo

## Estilo y Generación de Mensajes de Commit
Al generar sugerencias de mensajes de commit en GitHub Desktop y extensiones de desarrollo:

1. **Idioma OBLIGATORIO:** Español.
2. **Estándar OBLIGATORIO:** Conventional Commits (formato: `<tipo>: <descripción concisa en español>`).
3. **Tipos válidos:**
   - `docs:` Cambios o adiciones en documentación técnica y especificaciones (archivos en `docs/` o README).
   - `feat:` Nuevas funcionalidades o endpoints (FastAPI, frontend, herramientas del agente).
   - `fix:` Corrección de errores o bugs.
   - `chore:` Tareas de mantenimiento, dependencias, `.gitignore`, `.gitattributes`, configuración.
   - `refactor:` Reestructuración de código sin alterar funcionalidad externa.
   - `test:` Pruebas unitarias o de integración.
4. **Formato del título:**
   - En minúsculas después de los dos puntos.
   - Verbo en tiempo presente/infinitivo (ej. `docs: documentar levantamiento empírico y trazabilidad de requisitos`).
   - Longitud máxima del título: 72 caracteres.
   - Sin punto final en el título.
5. **Cuerpo del commit (opcional):**
   - Si el commit abarca más de un cambio relevante, listar viñetas explicativas en español.
6. **Declaración obligatoria de asistencia de IA (Rúbrica UNIANDES):**
   - Agregar siempre al final del cuerpo del commit:
     `Hecho con asistencia de IA; revisado por: [Nombre del integrante]`
