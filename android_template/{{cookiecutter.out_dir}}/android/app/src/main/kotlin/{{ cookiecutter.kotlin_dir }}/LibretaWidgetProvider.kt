package {{ cookiecutter.org_name_2 }}.{{ cookiecutter.package_name }}

import android.app.AlarmManager
import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.SystemClock
import android.view.View
import android.widget.RemoteViews
import org.json.JSONArray
import org.json.JSONObject
import org.json.JSONTokener
import java.io.File
import java.text.NumberFormat
import java.util.Locale

/**
 * Widget nativo de Libreta. No ejecuta Python: lee el snapshot que la app
 * escribe en SharedPreferences (clave flutter.libreta_widget) y lo pinta con
 * RemoteViews, que es lo único que el launcher permite.
 */
class LibretaWidgetProvider : AppWidgetProvider() {

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray
    ) {
        appWidgetIds.forEach { updateWidget(context, appWidgetManager, it) }
        scheduleTicks(context)
    }

    override fun onEnabled(context: Context) {
        scheduleTicks(context)
    }

    override fun onDisabled(context: Context) {
        cancelTicks(context)
    }

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)
        when (intent.action) {
            ACTION_REFRESH, ACTION_TICK -> updateAll(context)
        }
    }

    private fun updateAll(context: Context) {
        val manager = AppWidgetManager.getInstance(context)
        val ids = manager.getAppWidgetIds(
            ComponentName(context, LibretaWidgetProvider::class.java)
        )
        ids.forEach { updateWidget(context, manager, it) }
    }

    private fun updateWidget(
        context: Context,
        manager: AppWidgetManager,
        widgetId: Int
    ) {
        val views = RemoteViews(context.packageName, R.layout.libreta_widget)
        val raw = readSnapshot(context)

        if (raw.isNullOrBlank()) {
            views.setTextViewText(R.id.widget_amount, "Abre Sapardobank")
            views.setTextViewText(R.id.widget_remaining, "Configura tu widget")
            views.setTextViewText(R.id.widget_last, "Tus gastos aparecerán aquí.")
            views.setTextViewText(R.id.widget_progress_label, "")
            views.setViewVisibility(R.id.widget_progress, View.GONE)
            views.setTextViewText(R.id.widget_updated, "")
        } else {
            try {
                val json = parseJson(raw)
                bind(views, json)
            } catch (_: Exception) {
                views.setTextViewText(R.id.widget_amount, "Datos no disponibles")
                views.setTextViewText(R.id.widget_remaining, "Abre Sapardobank y publica el widget")
                views.setTextViewText(R.id.widget_last, "")
            }
        }

        views.setOnClickPendingIntent(R.id.widget_root, openApp(context))
        views.setOnClickPendingIntent(R.id.widget_refresh, refreshIntent(context))
        manager.updateAppWidget(widgetId, views)
    }

    /**
     * Flet/shared_preferences puede guardar el string tal cual o JSON-encoded
     * (con comillas y escapes). Aceptamos ambos casos.
     */
    private fun parseJson(raw: String): JSONObject {
        val trimmed = raw.trim()
        if (!trimmed.startsWith("\"")) return JSONObject(trimmed)
        val decoded = JSONTokener(trimmed).nextValue()
        return when (decoded) {
            is JSONObject -> decoded
            is String -> JSONObject(decoded)
            else -> JSONObject(trimmed)
        }
    }

    /**
     * Puente principal: archivo que escribe Python en
     * /data/data/<package>/files/data/widget_data.json.
     * Respaldo: SharedPreferences de Flutter.
     */
    private fun readSnapshot(context: Context): String? {
        val candidates = mutableListOf(
            File(context.filesDir, "data/widget_data.json"),
            File(context.filesDir, "data/widgets/widget_data.json"),
            File(context.filesDir, "data/widgets/libreta_widget_wide.json")
        )
        context.getExternalFilesDir(null)?.let {
            candidates.add(File(it, "widget_data.json"))
        }
        for (file in candidates) {
            try {
                if (file.isFile) return file.readText()
            } catch (_: Exception) {
                // sigue con el siguiente candidato
            }
        }
        val prefs = context.getSharedPreferences("FlutterSharedPreferences", Context.MODE_PRIVATE)
        return prefs.getString("flutter.libreta_widget", null)
    }

    private fun bind(views: RemoteViews, json: JSONObject) {
        val hidden = json.optBoolean("hidden", false)
        val symbol = json.optString("currency_symbol", "$")
        val spent = json.optLong("spent_today_cents", 0L)
        val budget = json.optLong("daily_budget_cents", 0L)
        val remaining = json.optLong("remaining_cents", 0L)
        val category = json.optString("top_category", "Sin gastos")
        val month = json.optLong("month_spent_cents", 0L)

        views.setTextViewText(R.id.widget_amount, money(spent, symbol, hidden))
        if (budget > 0L) {
            val pct = ((spent * 100) / budget).toInt().coerceIn(0, 100)
            views.setProgressBar(R.id.widget_progress, 100, pct, false)
            views.setViewVisibility(R.id.widget_progress, View.VISIBLE)
            views.setTextViewText(
                R.id.widget_progress_label,
                if (spent > budget) "Presupuesto excedido" else "$pct% del presupuesto de hoy"
            )
        } else {
            views.setViewVisibility(R.id.widget_progress, View.GONE)
            views.setTextViewText(R.id.widget_progress_label, "Sin presupuesto diario")
        }

        views.setTextViewText(
            R.id.widget_remaining,
            if (spent > budget && budget > 0L) "Gastado de más"
            else "Quedan " + money(remaining, symbol, hidden)
        )
        views.setTextViewText(R.id.widget_category, "$category · mes " + money(month, symbol, hidden))

        val last = json.optJSONArray("last_transactions")
        if (last != null && last.length() > 0) {
            val item = last.getJSONObject(0)
            val desc = item.optString("description", "Movimiento")
            val amount = item.optLong("amount_cents", 0L)
            views.setTextViewText(R.id.widget_last, "$desc  ·  " + money(amount, symbol, hidden))
        } else {
            views.setTextViewText(R.id.widget_last, "Sin movimientos todavía")
        }

        val updated = json.optString("updated_at", "")
        val time = if (updated.length >= 16) updated.substring(11, 16) else ""
        views.setTextViewText(
            R.id.widget_updated,
            if (time.isNotEmpty()) "Actualizado $time · toca ↻ para refrescar" else "Toca ↻ para refrescar"
        )
    }

    private fun money(cents: Long, symbol: String, hidden: Boolean): String {
        if (hidden) return "$symbol••••"
        val formatter = NumberFormat.getIntegerInstance(Locale.US)
        val absolute = kotlin.math.abs(cents) / 100
        val body = formatter.format(absolute)
        return if (cents < 0) "-$symbol$body" else "$symbol$body"
    }

    private fun openApp(context: Context): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        return PendingIntent.getActivity(
            context,
            1,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
    }

    private fun refreshIntent(context: Context): PendingIntent {
        val intent = Intent(context, LibretaWidgetProvider::class.java).apply {
            action = ACTION_REFRESH
        }
        return PendingIntent.getBroadcast(
            context,
            2,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
    }

    private fun scheduleTicks(context: Context) {
        val alarm = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val intent = Intent(context, LibretaWidgetProvider::class.java).apply {
            action = ACTION_TICK
        }
        val pending = PendingIntent.getBroadcast(
            context,
            3,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        // Cada 5 minutos, sin despertar el dispositivo de forma exacta.
        alarm.setInexactRepeating(
            AlarmManager.ELAPSED_REALTIME,
            SystemClock.elapsedRealtime() + 60_000L,
            5 * 60_000L,
            pending
        )
    }

    private fun cancelTicks(context: Context) {
        val alarm = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val intent = Intent(context, LibretaWidgetProvider::class.java).apply {
            action = ACTION_TICK
        }
        val pending = PendingIntent.getBroadcast(
            context,
            3,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        alarm.cancel(pending)
    }

    companion object {
        const val ACTION_REFRESH = "com.sapardobank.app.WIDGET_REFRESH"
        const val ACTION_TICK = "com.sapardobank.app.WIDGET_TICK"
    }
}
