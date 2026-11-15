package com.kitaab.reader.pdf

import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import android.util.LruCache
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.io.File

/**
 * An open PDF. PdfRenderer can only have one page open at a time, so every call
 * goes through [lock]. Rendered pages are kept in a memory-bounded cache.
 */
class PdfDocument private constructor(
    private val fd: ParcelFileDescriptor,
    private val renderer: PdfRenderer,
    /** Page sizes in PDF points, used to lay pages out before they are rendered. */
    val pageSizes: List<PageSize>,
) {
    data class PageSize(val width: Int, val height: Int) {
        val aspect: Float get() = if (height == 0) 0.707f else width.toFloat() / height
    }

    val pageCount: Int get() = pageSizes.size

    private val lock = Mutex()
    @Volatile private var closed = false

    private val cache = object : LruCache<String, Bitmap>(cacheBytes()) {
        override fun sizeOf(key: String, value: Bitmap) = value.allocationByteCount
    }

    /** Renders [index] so it is [widthPx] wide. Returns null if the document was closed. */
    suspend fun render(index: Int, widthPx: Int): Bitmap? {
        if (index !in pageSizes.indices || widthPx <= 0) return null
        val w = widthPx.coerceIn(64, MAX_WIDTH)
        val key = "$index@$w"
        cache.get(key)?.let { return it }
        return withContext(Dispatchers.IO) {
            lock.withLock {
                if (closed) return@withLock null
                cache.get(key)?.let { return@withLock it }
                renderer.openPage(index).use { page ->
                    val h = (w / pageSizes[index].aspect).toInt().coerceIn(1, MAX_WIDTH * 4)
                    val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
                    bmp.eraseColor(Color.WHITE)
                    page.render(bmp, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    cache.put(key, bmp)
                    bmp
                }
            }
        }
    }

    suspend fun close() {
        lock.withLock {
            if (closed) return
            closed = true
            runCatching { renderer.close() }
            runCatching { fd.close() }
            cache.evictAll()
        }
    }

    companion object {
        private const val MAX_WIDTH = 2600

        private fun cacheBytes(): Int {
            val max = Runtime.getRuntime().maxMemory()
            return (max / 5).coerceAtMost(Int.MAX_VALUE.toLong()).toInt()
        }

        suspend fun open(file: File): PdfDocument = withContext(Dispatchers.IO) {
            val fd = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
            try {
                val renderer = PdfRenderer(fd)
                val sizes = List(renderer.pageCount) { i ->
                    renderer.openPage(i).use { PageSize(it.width, it.height) }
                }
                PdfDocument(fd, renderer, sizes)
            } catch (e: Exception) {
                fd.close()
                throw e
            }
        }
    }
}
