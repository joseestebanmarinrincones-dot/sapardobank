# Plantilla Android de Sapardobank

Esta carpeta es una copia de la plantilla oficial de compilación de **Flet 1.0.5** con el widget nativo de Android añadido. Flet la usa con:

```powershell
flet build apk --template android_template
```

## Archivos añadidos

- `android/app/src/main/kotlin/{{ cookiecutter.kotlin_dir }}/LibretaWidgetProvider.kt`
  - `AppWidgetProvider` con `RemoteViews`.
  - Lee el JSON que Python escribe en `SharedPreferences` con la clave
    `flutter.libreta_widget`.
  - Se actualiza cada 5 minutos con `AlarmManager` y tiene un botón de refresco.
  - Abre la app al tocar el widget.
- `android/app/src/main/res/layout/libreta_widget.xml`
- `android/app/src/main/res/xml/libreta_widget_info.xml`
- `android/app/src/main/res/drawable/libreta_widget_bg.xml`
- `android/app/src/main/res/drawable/libreta_widget_refresh_bg.xml`
- `android/app/src/main/res/values/libreta_widget_strings.xml`
- `AndroidManifest.xml`: permiso `INTERNET`, receiver del widget y
  `usesCleartextTraffic="false"`.

## Actualizar Flet

La plantilla está acoplada a la versión de Flet (1.0.5). Si actualizas Flet:

1. Descarga la plantilla de la nueva versión:
   `https://github.com/flet-dev/flet/releases/download/vX.Y.Z/flet-build-template.zip`
2. Reemplaza el contenido de `android_template/`.
3. Vuelve a copiar los archivos del widget y los cambios del manifiesto.
4. Compila y prueba el widget en un dispositivo real.

## Depuración

- Si el widget muestra “Abre Sapardobank”, abre la app y pulsa **Widget → Publicar widget**.
- Si el launcher no lo muestra, verifica que el APK se compiló con esta plantilla
  (no con la plantilla estándar) y que el receptor está en el manifiesto.
- El widget no puede ejecutar Python: solo pinta el último snapshot guardado.
- En Android 12+ el launcher puede tardar en mostrar el preview; el widget
  aparece igualmente en la lista de widgets.
