# Sapardobank 1.0.0

Primera versión pública de **Sapardobank**, una libreta de gastos diaria escrita en Python con Flet.

## Incluye

- Gastos e ingresos, cuentas, categorías, presupuesto diario y reportes.
- 6 temas de color aplicables al instante.
- Tutorial integrado de 4 pasos con **Atrás**, **Siguiente** y **Saltar** para conectar internet y el banco.
- Modo demostración con compras simuladas en tiempo real.
- Backend opcional con Plaid, webhooks HMAC, SSE y firewall de red.
- Widget nativo Android con gasto de hoy, presupuesto y último movimiento.
- Datos locales en SQLite; la nube es opcional.

## APK

- `Sapardobank-1.0.0.apk`
- Android 7+ (minSdk 24), universal: arm64-v8a, armeabi-v7a, x86_64.
- Firma **debug**: instala fuera de Play Store; Android puede pedir permitir la fuente.
- SHA-256: `76DBA2754BEB0F89F07253CEEBF09D91ABDD7D73B4B905E0F7F4D1AA244AF9AE`

## Notas

- La app funciona sin internet con el modo demo.
- Para banca real necesitas desplegar el servidor (`server/`) con HTTPS y configurar Plaid o un webhook/Belvo.
- Cada instalación tiene su propia base de datos local. No incluye tokens ni datos del autor.
- El widget nativo se agrega desde el launcher: mantén presionado el inicio → Widgets → Sapardobank.
- El código fuente y las instrucciones están en el repositorio.
