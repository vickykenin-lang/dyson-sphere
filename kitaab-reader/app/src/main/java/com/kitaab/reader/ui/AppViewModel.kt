package com.kitaab.reader.ui

import android.app.Application
import android.net.Uri
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.kitaab.reader.data.Library
import com.kitaab.reader.data.ReaderPrefs
import com.kitaab.reader.data.ReaderSettings
import com.kitaab.reader.data.SortOrder
import com.kitaab.reader.pdf.PdfDocument
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

sealed interface Screen {
    data object Library : Screen
    data class Reader(val bookId: String) : Screen
}

sealed interface ReaderState {
    data object Loading : ReaderState
    data class Ready(val doc: PdfDocument) : ReaderState
    data class Error(val message: String) : ReaderState
}

class AppViewModel(app: Application) : AndroidViewModel(app) {

    val library = Library(app)
    private val prefs = ReaderPrefs(app)

    var screen by mutableStateOf<Screen>(Screen.Library)
        private set
    var readerState by mutableStateOf<ReaderState>(ReaderState.Loading)
        private set
    var settings by mutableStateOf(prefs.load())
        private set
    var sort by mutableStateOf(prefs.sort)
        private set
    var importing by mutableStateOf(0)
        private set

    private val _messages = Channel<String>(Channel.BUFFERED)
    val messages = _messages.receiveAsFlow()

    private var openJob: Job? = null
    private var openDoc: PdfDocument? = null

    // Survives the ViewModel so a document is always closed, even while the app is going away.
    private val closer = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    fun import(uris: List<Uri>, openWhenSingle: Boolean = false) {
        if (uris.isEmpty()) return
        viewModelScope.launch {
            importing += uris.size
            var added = 0
            var last: String? = null
            for (uri in uris) {
                when (val r = library.import(uri)) {
                    is Library.ImportResult.Added -> { added++; last = r.book.id }
                    is Library.ImportResult.AlreadyThere -> {
                        last = r.book.id
                        if (!openWhenSingle || uris.size > 1) _messages.send("“${r.book.title}” is already on your shelf")
                    }
                    is Library.ImportResult.Failed -> _messages.send("${r.name}: ${r.reason}")
                }
                importing -= 1
            }
            if (added > 1) _messages.send("$added books added")
            else if (added == 1 && !openWhenSingle) _messages.send("Book added")
            if (openWhenSingle && uris.size == 1) last?.let { open(it) }
        }
    }

    fun open(bookId: String) {
        val book = library.get(bookId) ?: return
        closeDocument()
        screen = Screen.Reader(book.id)
        readerState = ReaderState.Loading
        openJob = viewModelScope.launch {
            library.markOpened(book.id)
            readerState = try {
                val doc = PdfDocument.open(library.pdfFile(book.id))
                openDoc = doc
                ReaderState.Ready(doc)
            } catch (e: Exception) {
                ReaderState.Error("This book could not be opened.")
            }
        }
    }

    fun closeReader() {
        closeDocument()
        screen = Screen.Library
    }

    private fun closeDocument() {
        openJob?.cancel()
        openJob = null
        val doc = openDoc
        openDoc = null
        readerState = ReaderState.Loading
        if (doc != null) closer.launch { doc.close() }
    }

    fun savePosition(bookId: String, page: Int) {
        viewModelScope.launch { withContext(NonCancellable) { library.savePosition(bookId, page) } }
    }

    fun toggleBookmark(bookId: String, page: Int) {
        viewModelScope.launch { library.toggleBookmark(bookId, page) }
    }

    fun rename(bookId: String, title: String) {
        viewModelScope.launch { library.rename(bookId, title) }
    }

    fun delete(bookId: String) {
        viewModelScope.launch {
            val title = library.get(bookId)?.title
            library.delete(bookId)
            if (title != null) _messages.send("Removed “$title”")
        }
    }

    fun updateSettings(s: ReaderSettings) {
        settings = s
        prefs.save(s)
    }

    fun updateSort(s: SortOrder) {
        sort = s
        prefs.sort = s
    }

    override fun onCleared() {
        openDoc?.let { doc -> closer.launch { doc.close() } }
        openDoc = null
    }
}
