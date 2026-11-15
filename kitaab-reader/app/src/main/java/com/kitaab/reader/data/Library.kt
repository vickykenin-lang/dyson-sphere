package com.kitaab.reader.data

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.ParcelFileDescriptor
import android.provider.OpenableColumns
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import org.json.JSONArray
import java.io.File
import java.io.FileOutputStream
import java.util.UUID

/**
 * The bookshelf. Every imported PDF is copied to `files/books/<id>.pdf`, its cover to
 * `files/covers/<id>.png`, and the list itself to `files/library.json`.
 */
class Library(private val context: Context) {

    private val booksDir = File(context.filesDir, "books").apply { mkdirs() }
    private val coversDir = File(context.filesDir, "covers").apply { mkdirs() }
    private val indexFile = File(context.filesDir, "library.json")
    private val writeLock = Mutex()

    private val _books = MutableStateFlow(load())
    val books: StateFlow<List<Book>> = _books.asStateFlow()

    fun pdfFile(id: String) = File(booksDir, "$id.pdf")
    fun coverFile(id: String) = File(coversDir, "$id.png")
    fun get(id: String): Book? = _books.value.firstOrNull { it.id == id }

    sealed interface ImportResult {
        data class Added(val book: Book) : ImportResult
        data class AlreadyThere(val book: Book) : ImportResult
        data class Failed(val name: String, val reason: String) : ImportResult
    }

    /** Copies the PDF behind [uri] into the library. Safe to call from the main thread. */
    suspend fun import(uri: Uri): ImportResult = withContext(Dispatchers.IO) {
        val name = displayName(uri)
        val title = name.removeSuffix(".pdf").removeSuffix(".PDF").replace('_', ' ').trim().ifEmpty { "Untitled" }
        val id = UUID.randomUUID().toString()
        val target = pdfFile(id)
        try {
            val input = context.contentResolver.openInputStream(uri)
                ?: return@withContext ImportResult.Failed(name, "The file could not be opened.")
            input.use { inp -> FileOutputStream(target).use { out -> inp.copyTo(out, 64 * 1024) } }

            // Same title and same size as a book already on the shelf: treat it as that book.
            val size = target.length()
            _books.value.firstOrNull { it.title == title && it.sizeBytes == size }?.let {
                target.delete()
                return@withContext ImportResult.AlreadyThere(it)
            }

            val pages = ParcelFileDescriptor.open(target, ParcelFileDescriptor.MODE_READ_ONLY).use { fd ->
                PdfRenderer(fd).use { renderer ->
                    renderCover(renderer, coverFile(id))
                    renderer.pageCount
                }
            }
            if (pages <= 0) {
                target.delete()
                return@withContext ImportResult.Failed(name, "The PDF has no pages.")
            }
            val book = Book(id = id, title = title, pageCount = pages, sizeBytes = size)
            mutate { listOf(book) + it }
            ImportResult.Added(book)
        } catch (e: SecurityException) {
            cleanup(id)
            ImportResult.Failed(name, "This PDF is password protected.")
        } catch (e: Exception) {
            cleanup(id)
            ImportResult.Failed(name, "This is not a readable PDF.")
        }
    }

    suspend fun rename(id: String, newTitle: String) {
        val t = newTitle.trim()
        if (t.isEmpty()) return
        mutate { list -> list.map { if (it.id == id) it.copy(title = t) else it } }
    }

    suspend fun delete(id: String) {
        mutate { list -> list.filterNot { it.id == id } }
        withContext(Dispatchers.IO) { cleanup(id) }
    }

    suspend fun markOpened(id: String) =
        mutate { list -> list.map { if (it.id == id) it.copy(lastOpenedAt = System.currentTimeMillis()) else it } }

    suspend fun savePosition(id: String, page: Int) =
        mutate { list -> list.map { if (it.id == id && it.lastPage != page) it.copy(lastPage = page) else it } }

    suspend fun toggleBookmark(id: String, page: Int) = mutate { list ->
        list.map {
            if (it.id != id) it
            else if (page in it.bookmarks) it.copy(bookmarks = it.bookmarks - page)
            else it.copy(bookmarks = (it.bookmarks + page).sorted())
        }
    }

    private suspend fun mutate(change: (List<Book>) -> List<Book>) = writeLock.withLock {
        _books.update(change)
        val snapshot = _books.value
        withContext(Dispatchers.IO) {
            val json = JSONArray().apply { snapshot.forEach { put(it.toJson()) } }.toString()
            val tmp = File(indexFile.path + ".tmp")
            tmp.writeText(json)
            tmp.renameTo(indexFile)
        }
    }

    private fun load(): List<Book> = try {
        if (!indexFile.exists()) emptyList()
        else {
            val arr = JSONArray(indexFile.readText())
            List(arr.length()) { Book.fromJson(arr.getJSONObject(it)) }.filter { pdfFile(it.id).exists() }
        }
    } catch (e: Exception) {
        emptyList()
    }

    private fun cleanup(id: String) {
        pdfFile(id).delete()
        coverFile(id).delete()
    }

    private fun displayName(uri: Uri): String {
        if (uri.scheme == "content") {
            runCatching {
                context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
                    if (c.moveToFirst()) {
                        val i = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                        if (i >= 0) c.getString(i)?.let { return it }
                    }
                }
            }
        }
        return uri.lastPathSegment?.substringAfterLast('/') ?: "Untitled.pdf"
    }

    private fun renderCover(renderer: PdfRenderer, out: File) {
        if (renderer.pageCount == 0) return
        renderer.openPage(0).use { page ->
            val w = 360
            val h = (w * page.height.toFloat() / page.width).toInt().coerceIn(1, w * 3)
            val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
            bmp.eraseColor(Color.WHITE)
            page.render(bmp, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
            FileOutputStream(out).use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
            bmp.recycle()
        }
    }
}
