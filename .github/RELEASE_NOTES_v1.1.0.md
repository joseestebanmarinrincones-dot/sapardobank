# Sapardobank 1.1.0

Segunda versión pública: arranque limpio, conexión a la red de casa con permiso y aviso de actualizaciones.

## Incluye

- **Arranque sin datos demo:** la app inicia con una cuenta "Mi efectivo" en cero y sin movimientos. La demo ahora es opcional.
- **Conectar a mi casa:** busca el servidor Sapardobank en el mismo Wi-Fi, pide permiso de red y guarda la conexión.
- **Permiso de red:** aviso dentro de la app antes de usar la red local o activar internet.
- **Aviso de actualización:** pop-up con la nueva versión y botón para descargar el APK desde GitHub.
- Gastos e ingresos, cuentas, categorías, presupuesto diario, reportes y 6 temas.
- Tutorial de 4 pasos con **Atrás**, **Siguiente** y **Saltar**.
- Backend opcional con Plaid, webhooks HMAC, SSE y firewall de red.
- Widget nativo Android.

## APK

- `Sapardobank-1.1.0.apk`
- Android 7+ (minSdk 24), universal: arm64-v8a, armeabi-v7a, x86_64.
- Firma **debug**: instala fuera de Play Store; Android puede pedir permitir la fuente.
- SHA-256: 427363EA90C7DDB88BA8025A05F29C6D62D8995D29CE6A41ACD79C5605C6DA3F

## Notas

- Para conectar la casa: ejecuta `run_server.bat` en la PC, deja PC y teléfono en el mismo Wi-Fi, abre **Ajustes → Conexión → Conectar a mi casa** y pega el token de `server_data/token.txt`.
- Para banca real necesitas configurar Plaid o un webhook/Belvo en el servidor.
- Cada instalación tiene su propia base de datos local.
- El widget nativo se agrega desde el launcher: mantén presionado el inicio → Widgets → Sapardobank.
- El código fuente y las instrucciones están en el repositorio.
