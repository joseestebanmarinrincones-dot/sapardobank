# Sapardobank

**Sapardobank: libreta de gastos diaria, local-first y escrita en Python.**  
Una app móvil con cuentas, presupuesto, reportes, temas, sincronización bancaria en tiempo real y un widget nativo para Android.

> Hecha con **Python + Flet**. En el teléfono corre Python dentro de la app (no es una web disfrazada): tus datos viven primero en SQLite, en tu dispositivo.

## APK listo para compartir

**`dist/Sapardobank-1.1.0.apk`** (también copiado en tu Escritorio como `Sapardobank-1.1.0.apk`).

- Versión 1.1.0 · Android 7+ (minSdk 24) · universal (arm64-v8a, armeabi-v7a, x86_64).
- Tamaño: 148.7 MB · Firma **debug** (instalable fuera de Play Store).
- SHA-256: `427363EA90C7DDB88BA8025A05F29C6D62D8995D29CE6A41ACD79C5605C6DA3F`
- Cada compañero instala el APK y usa su propia libreta local; no incluye tu token ni tus datos.
- Android puede mostrar un aviso de “app no verificada” por no venir de Play Store. Es normal: permite la instalación desde esa fuente.
- **Arranque limpio:** no se cargan gastos demo al abrir; solo una cuenta “Mi efectivo” en cero. La demo se activa manualmente.
- **Conexión a casa:** Ajustes → Conexión → Conectar a mi casa. Pide permiso de red y busca el servidor en tu Wi-Fi.
- **Avisos de actualización:** si hay una versión nueva en GitHub, aparece un pop-up con botón Descargar.
- **GitHub y descargas:** https://github.com/joseestebanmarinrincones-dot/sapardobank/releases/latest

---

## Tutorial dentro de la app

La primera vez que se abre Sapardobank aparece un tutorial de **4 pasos** para conectar internet y el banco, con botones **Atrás**, **Siguiente** y **Saltar**:

1. Qué se necesita y cómo probar el modo demo.
2. Cómo buscar el servidor en el Wi-Fi de casa y pegar el token.
3. Cómo vincular el banco con Plaid, Belvo o webhook.
4. Cómo sincronizar y ver los gastos en el widget.

Puedes repetirlo cuando quieras en **Ajustes → Conexión → Tutorial**.

---

## Lo que incluye

- **Libreta diaria:** gastos e ingresos, categorías, cuentas, notas, fecha y edición.
- **Inicio inteligente:** gasto de hoy, presupuesto restante, semana, categorías y saldos.
- **Movimientos:** búsqueda, filtros, navegación por mes y edición/borrado.
- **Reportes:** comparativa mensual, últimas 8 semanas, mezcla por categoría y proyección.
- **Cuentas:** efectivo, débito, crédito, ahorro y cuentas vinculadas.
- **Temas:** 6 paletas de color aplicadas al instante (Esmeralda, Océano, Lavanda, Terracota, Grafito, Cereza).
- **Widget nativo Android:** gasto de hoy, presupuesto y último movimiento en la pantalla de inicio.
- **Modo demostración:** genera compras simuladas en tiempo real sin conectar un banco.
- **Backend opcional:** sincronización, SSE, Plaid y webhooks firmados.
- **Firewall de red:** HTTPS en internet, HTTP solo LAN, allowlist de salida, bloqueo de IP privadas, rate limiting, token y HMAC.

---

## Inicio rápido (Windows)

Requisitos: **Python 3.12**.

```bat
run_windows.bat
```

O manualmente:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

En el primer arranque la libreta está **vacía**: solo verás la cuenta “Mi efectivo” en cero. La demostración se carga manualmente desde **Ajustes → Datos → Cargar demostración** o activando **Modo demostración**.

Para desarrollar con recarga en caliente:

```powershell
.venv\Scripts\flet run main.py
.venv\Scripts\flet run --web main.py
```

---

## App Android y widget nativo

### Compilar el APK

```bat
build_android.bat
```

o:

```powershell
$env:PYTHONIOENCODING="utf-8"
.venv\Scripts\flet build apk --template android_template --yes --no-rich-output
```

La primera compilación descarga **Flutter, el SDK de Android y JDK** automáticamente. Puede tardar entre 10 y 40 minutos y ocupar varios GB. También necesita **Git** en el `PATH` (Flutter lo usa para calcular su versión); instálalo con `winget install Git.Git` y vuelve a abrir la terminal. El APK queda en `build\apk\`.

> **Windows y symlinks:** si el build se detiene con *“Building with plugins requires symlink support”*, activa el **Modo desarrollador** (Configuración → Sistema → Para desarrolladores) y vuelve a intentarlo, o abre la terminal como administrador. Sin permisos de administrador puedes ejecutar `python tools\prepare_plugin_junctions.py` y reintentar el build; es la alternativa usada para generar el APK de este proyecto.

El proyecto usa una **plantilla Android propia** (`android_template/`) que añade:

- `LibretaWidgetProvider.kt` (widget nativo con `RemoteViews`).
- Layout, fondo, progreso y recursos del widget.
- Permiso `INTERNET` y `usesCleartextTraffic="true"` (la app solo permite HTTP hacia la red local; internet sigue exigiendo HTTPS).
- Receiver registrado en `AndroidManifest.xml`.

La plantilla está fijada a **Flet 1.0.5**. Si actualizas Flet, vuelve a generar `android_template/` desde la plantilla oficial y reaplica los archivos del widget.

### Instalar y agregar el widget

1. Instala el APK en tu Android (permite “instalar apps desconocidas” para el explorador de archivos).
2. Abre Sapardobank y toca **Widget** en Inicio, o **Ajustes → Widget**.
3. Elige formato y tema, y pulsa **Publicar widget**.
4. Mantén presionado el escritorio → **Widgets** → **Sapardobank** → arrastra el widget.
5. El widget lee el snapshot local, se actualiza cada 5 minutos y tiene un botón **↻** para refrescar al instante.

> El widget nativo está incluido **solo si compilas con `--template android_template`**. Si compilas con la plantilla estándar de Flet, la app funciona, pero el launcher no mostrará el widget de Sapardobank. En ese caso puedes usar **Guardar imagen** y colocarla con un widget de Fotos/Galería.

### Compartir el APK con tus compañeros

Copia `build\apk\sapardobank.apk` (o el nombre que genere Flet) y compártelo por Drive, WhatsApp o USB. También puedes renombrarlo a `Sapardobank-1.1.0.apk`.

- Es un APK **firmado en modo debug**: se instala sin Play Store, pero Android puede mostrar “app no verificada” o pedir permitir la instalación desde esa fuente. Es normal.
- Cada compañero tiene su **propia base de datos local**. No necesitan tu servidor ni tu token para probar la app con el modo demo.
- **No compartas tu token del servidor ni tu `.env`**. Si quieren banca real, cada uno debe desplegar su servidor o recibir un token propio (el servidor actual es de un solo usuario).
- Para actualizar la app más adelante, usa la misma firma (mismo equipo/keystore) para que Android permita la actualización sin desinstalar.

Si quieres una firma de producción, añade un keystore:

```powershell
keytool -genkey -v -keystore sapardobank-release.jks -keyalg RSA -keysize 2048 -validity 10000 -alias sapardobank
```

y compila con las variables `FLET_ANDROID_SIGNING_KEY_STORE`, `FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD`, `FLET_ANDROID_SIGNING_KEY_PASSWORD` y `FLET_ANDROID_SIGNING_KEY_ALIAS`.

### iOS

`flet build ipa` se ejecuta en macOS. La app funciona, pero el widget nativo de iOS (`WidgetKit`) requeriría una extensión Swift adicional que no está incluida. En iOS usa el widget visual: **Ajustes → Widget → Guardar imagen** y un widget de Fotos.

---

## Servidor y acceso a internet

El servidor es **opcional**: la app funciona 100 % local. Se necesita para banca real, sincronización entre dispositivos y webhooks.

### Arrancar

```powershell
copy .env.example .env
# Edita .env: token, URL pública, Plaid, secretos
run_server.bat
```

o:

```powershell
.venv\Scripts\uvicorn server.main:app --host 0.0.0.0 --port 8787
```

Comprueba:

```powershell
curl http://127.0.0.1:8787/health
```

Si no defines `LIBRETA_API_TOKEN`, el servidor genera uno en `server_data/token.txt`. Ese token se pega en **Ajustes → Conexión** de la app.

### HTTPS

La app permite HTTP **solo** en la red local; para internet el servidor debe exponerse por **HTTPS** (Caddy, Nginx o un túnel). Para pruebas en red local, `RemoteClient` permite HTTP solo si el host es loopback o una IP privada; en un teléfono real, `127.0.0.1` es el teléfono, no tu PC: usa la IP LAN del PC o HTTPS.

Ejemplo mínimo con Caddy:

```caddy
sapardobank.tu-dominio.com {
    reverse_proxy 127.0.0.1:8787
}
```

Configura `LIBRETA_PUBLIC_BASE_URL=https://sapardobank.tu-dominio.com` para que Plaid pueda enviar webhooks y para que el enlace de vinculación sea público.

### Firewall incluido

No es un firewall del sistema operativo (Android/iOS no lo permiten a una app). Es un **firewall de aplicación** en dos capas:

**En el servidor (`server/firewall.py`)**
- Solo salidas **HTTPS**.
- Allowlist explícita (`sandbox.plaid.com`, `production.plaid.com`).
- Resolución DNS y bloqueo de loopback, privadas, link-local, multicast y reservadas (mitiga SSRF).
- Sin redirecciones, TLS verificado y timeout.
- Auditoría de cada intento en `firewall_log` (`/v1/security/audit`).

**En el perímetro (`server/security.py`)**
- Token Bearer para la app.
- Rate limiting por IP y límite de payload.
- Webhooks firmados con **HMAC-SHA256**.
- `X-Frame-Options`, `nosniff`, `Referrer-Policy` y `Cache-Control: no-store` en la API.
- URL de webhook de Plaid con secreto de ruta generado automáticamente.

**En la app**
- Valida HTTPS (salvo loopback/privadas para desarrollo).
- El manifiesto Android bloquea tráfico en claro.
- Internet está **desactivado por defecto**.

---

## Conectar a mi casa

1. En la computadora, abre `run_server.bat`. Anota el token de `server_data/token.txt`.
2. Deja la PC y el teléfono en la **misma red Wi-Fi**.
3. En la app: **Ajustes → Conexión → Conectar a mi casa**.
4. Acepta el **permiso de red** que solicita la app (es un aviso dentro de Sapardobank; Android no pregunta por INTERNET porque es un permiso de instalación).
5. Sapardobank escanea tu Wi-Fi, encuentra el servidor y te pide el token.
6. Pulsa **Conectar**. La URL, el token y el permiso quedan guardados; al abrir la app se sincroniza sola.

Si no aparece, revisa que el firewall de Windows permita el puerto **8787** y que el servidor esté escuchando en `0.0.0.0`. También puedes escribir la URL manualmente en el mismo formulario.

## Avisos de actualización

La app consulta la última release pública de GitHub (solo si el usuario dio permiso de red) y, cuando hay una versión nueva, muestra un **pop-up** con:

- **Ahora no**: no vuelve a molestar con esa versión.
- **Descargar**: abre el APK en el navegador para instalarlo.

Puedes desactivar la búsqueda o probar el aviso desde **Ajustes → Actualizaciones**.

## Vincular un banco

### Opción A: Plaid (recomendado para EE. UU., Canadá y Europa)

1. Crea una cuenta en [Plaid](https://dashboard.plaid.com/) y obtén `client_id` y `secret` de **Sandbox**.
2. En `.env`:
   ```env
   LIBRETA_PLAID_CLIENT_ID=...
   LIBRETA_PLAID_SECRET=...
   LIBRETA_PLAID_ENV=sandbox
   LIBRETA_PLAID_COUNTRIES=US,CA
   LIBRETA_PUBLIC_BASE_URL=https://tu-servidor
   ```
3. Reinicia el servidor.
4. En la app: **Ajustes → Conexión**, guarda URL y token, activa internet.
5. **Cuentas → Vincular un banco → Abrir vinculación**.
6. Termina en Plaid y vuelve a Sapardobank; toca **Sincronizar**.

Plaid exige HTTPS público para webhooks. En sandbox puedes usar sus credenciales de prueba. La disponibilidad de países depende de Plaid; si tu banco no está cubierto, usa webhooks.

### Opción B: webhook / Belvo / banco directo

El endpoint es:

```text
POST https://tu-servidor/v1/webhooks/bank
X-Libreta-Signature: sha256=<hmac_hex>
```

El secreto está en `server_data/bank_webhook_secret.txt` (o `LIBRETA_BANK_WEBHOOK_SECRET`).

Payload:

```json
{
  "event_id": "evt_123",
  "account": {
    "id": "acc_banco_1",
    "name": "Cuenta principal",
    "institution": "Mi Banco",
    "currency": "MXN",
    "balance_cents": 1234500,
    "provider": "belvo"
  },
  "transactions": [
    {
      "external_id": "tx_987",
      "amount_cents": -4500,
      "description": "Café",
      "merchant": "Café Central",
      "category_id": "coffee",
      "occurred_at": "2026-10-30T09:15:00",
      "pending": false
    }
  ]
}
```

- `amount_cents` negativo = gasto; positivo = ingreso.
- `external_id` evita duplicados.
- La firma se calcula sobre el **cuerpo crudo**:

```powershell
$body = Get-Content payload.json -Raw
$secret = Get-Content server_data/bank_webhook_secret.txt -Raw
$hmac = [System.Security.Cryptography.HMACSHA256]::new([Text.Encoding]::UTF8.GetBytes($secret.Trim()))
$sig = ($hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($body)) | ForEach-Object { $_.ToString("x2") }) -join ""
Invoke-WebRequest -Uri "https://tu-servidor/v1/webhooks/bank" -Method POST -Body $body -ContentType "application/json" -Headers @{ "X-Libreta-Signature" = "sha256=$sig" }
```

Cada movimiento nuevo se empuja a la app por **SSE** (`/v1/events`) y se refleja en el widget.

### Opción C: modo demo (opcional)

No requiere servidor. Carga la demo desde **Ajustes → Datos → Cargar demostración** o activa el modo demo en **Cuentas**. El feed local genera una compra cada 75 s (configurable) y actualiza la UI y el widget.

---

## Temas

**Ajustes → Apariencia → Color de la app.** Hay 6 paletas y el cambio es inmediato: fondo, tarjetas, botones, barra de navegación, gráficas y acentos. La elección se guarda en SQLite y se aplica al reiniciar.

Los colores de las categorías se mantienen estables para que los reportes sigan siendo reconocibles. El widget conserva sus temas propios (Bosque, Papel, Noche) para que combine con el escritorio.

---

## Arquitectura

```text
Sapardobank/
  main.py                 entrada Flet
  libreta/
    core/                 SQLite, modelos, dinero, fechas, datos demo
    services/             ledger, dashboard, sync, widget, export, demo
    ui/                   tema, componentes, vistas, hojas modales
  server/
    main.py               FastAPI, SSE, Plaid, webhooks
    firewall.py           allowlist HTTPS / anti-SSRF
    security.py           token, HMAC, rate limit, headers
    providers/plaid.py    /transactions/sync
    static/link.html      portal de Plaid
  android_template/       plantilla Flutter + widget Kotlin
  tests/                  41 pruebas de dominio, servidor y seguridad
```

### Flujo de datos

1. La app escribe en **SQLite local** (WAL, conexiones cortas).
2. Si internet está activo, `SyncManager` empuja cuentas/movimientos manuales y recibe los del servidor.
3. Plaid/webhook actualiza el servidor y publica un evento SSE.
4. La app aplica el evento por `external_id` (idempotente) y reconstruye la vista.
5. `WidgetService` escribe el snapshot en `SharedPreferences`; el widget Android lo lee sin ejecutar Python.

### Dónde están tus datos

- Windows: `%LOCALAPPDATA%\LibretaGastos\libreta.db`
- Android: almacenamiento privado de la app (`FLET_APP_STORAGE_DATA`)
- Servidor: `server_data/server.db`
- Widget: `server_data` no; en el teléfono, `SharedPreferences` con la clave `flutter.libreta_widget`.

Puedes exportar los movimientos a CSV desde **Reportes** o **Ajustes**.

---

## Seguridad y límites (léelo)

- **No es una app bancaria certificada.** Es un proyecto personal; revisa el código antes de usarlo con dinero real.
- **No se guardan usuarios ni contraseñas bancarias** en el teléfono. Plaid/webhook maneja la autorización.
- En el servidor, los `access_token` de Plaid se guardan en SQLite. Para producción: cifra el disco, restringe permisos, usa HTTPS y rota secretos.
- El token de la app se guarda en SQLite del teléfono. Si tu amenaza incluye un dispositivo comprometido, usa el bloqueo del sistema y considera un almacén de claves nativo.
- El webhook de Plaid se protege con **secreto de ruta + TLS**. Para producción se recomienda además verificar la firma JWT de Plaid (no implementada) o poner el servidor detrás de un proxy con reglas.
- El widget nativo es de **Android**. En iOS solo está el widget visual exportable.
- El firewall es de aplicación, no reemplaza el firewall del sistema operativo ni un WAF.
- El modo demo genera datos falsos; no los mezcles con tu contabilidad real.

---

## Pruebas

```powershell
.venv\Scripts\python -m pytest -q
```

Cubre dinero/formatos, ledger, presupuesto, widget, deduplicación, firewall, Plaid mapping, sync y webhooks HMAC.

Prueba end-to-end del servidor:

```powershell
# En una terminal:
$env:LIBRETA_API_TOKEN="test-token"
.venv\Scripts\uvicorn server.main:app --port 8788

# En otra:
.venv\Scripts\python tools\integration_server.py
```

---

## Créditos

- [Flet](https://flet.dev) — UI multiplataforma en Python.
- [Plaid](https://plaid.com) — agregación bancaria.
- Fuentes **DM Serif Display** y **Lato** con licencia SIL OFL (incluidas en `assets/fonts`).
- Iconos Material Symbols vía Flet.

Hecho con cariño para que tu dinero tenga una libreta, no una niebla.
