package com.kitaab.reader.data

import android.content.Context

enum class PaperTheme { DAY, SEPIA, NIGHT }
enum class PageMode { FLIP, SCROLL }
enum class SortOrder { RECENT, TITLE, ADDED }

data class ReaderSettings(
    val theme: PaperTheme = PaperTheme.DAY,
    val mode: PageMode = PageMode.FLIP,
    val volumeKeysTurnPages: Boolean = true,
    val keepScreenOn: Boolean = true,
)

class ReaderPrefs(context: Context) {
    private val sp = context.getSharedPreferences("reader", Context.MODE_PRIVATE)

    fun load() = ReaderSettings(
        theme = enumOr(sp.getString("theme", null), PaperTheme.DAY),
        mode = enumOr(sp.getString("mode", null), PageMode.FLIP),
        volumeKeysTurnPages = sp.getBoolean("volumeKeys", true),
        keepScreenOn = sp.getBoolean("keepScreenOn", true),
    )

    fun save(s: ReaderSettings) = sp.edit()
        .putString("theme", s.theme.name)
        .putString("mode", s.mode.name)
        .putBoolean("volumeKeys", s.volumeKeysTurnPages)
        .putBoolean("keepScreenOn", s.keepScreenOn)
        .apply()

    var sort: SortOrder
        get() = enumOr(sp.getString("sort", null), SortOrder.RECENT)
        set(v) = sp.edit().putString("sort", v.name).apply()

    private inline fun <reified T : Enum<T>> enumOr(name: String?, fallback: T): T =
        name?.let { n -> enumValues<T>().firstOrNull { it.name == n } } ?: fallback
}
