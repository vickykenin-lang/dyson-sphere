package com.kitaab.reader.data

import org.json.JSONArray
import org.json.JSONObject

/** One PDF in the library. The PDF itself is copied into the app's private storage. */
data class Book(
    val id: String,
    val title: String,
    val pageCount: Int,
    /** Zero-based page the reader was on when the book was last closed. */
    val lastPage: Int = 0,
    val addedAt: Long = System.currentTimeMillis(),
    /** 0 means the book has never been opened. */
    val lastOpenedAt: Long = 0L,
    val bookmarks: List<Int> = emptyList(),
    val sizeBytes: Long = 0L,
) {
    /** Reading progress from 0 to 1, counting the current page as read. */
    val progress: Float
        get() = if (pageCount <= 0) 0f else ((lastPage + 1).toFloat() / pageCount).coerceIn(0f, 1f)

    val isFinished: Boolean get() = pageCount > 0 && lastPage >= pageCount - 1

    fun toJson(): JSONObject = JSONObject()
        .put("id", id)
        .put("title", title)
        .put("pageCount", pageCount)
        .put("lastPage", lastPage)
        .put("addedAt", addedAt)
        .put("lastOpenedAt", lastOpenedAt)
        .put("bookmarks", JSONArray(bookmarks))
        .put("sizeBytes", sizeBytes)

    companion object {
        fun fromJson(o: JSONObject): Book {
            val marks = o.optJSONArray("bookmarks")
            return Book(
                id = o.getString("id"),
                title = o.getString("title"),
                pageCount = o.getInt("pageCount"),
                lastPage = o.optInt("lastPage", 0),
                addedAt = o.optLong("addedAt", 0L),
                lastOpenedAt = o.optLong("lastOpenedAt", 0L),
                bookmarks = if (marks == null) emptyList() else List(marks.length()) { marks.getInt(it) },
                sizeBytes = o.optLong("sizeBytes", 0L),
            )
        }
    }
}
