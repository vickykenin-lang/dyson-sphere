package com.kitaab.reader.ui.library

import android.graphics.BitmapFactory
import android.text.format.DateUtils
import android.util.LruCache
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.MenuBook
import androidx.compose.material.icons.automirrored.filled.Sort
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.kitaab.reader.data.Book
import com.kitaab.reader.data.Library
import com.kitaab.reader.data.SortOrder
import com.kitaab.reader.ui.AppViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LibraryScreen(vm: AppViewModel, snackbar: SnackbarHostState) {
    val books by vm.library.books.collectAsStateWithLifecycle()
    var searching by rememberSaveable { mutableStateOf(false) }
    var query by rememberSaveable { mutableStateOf("") }
    var menuFor by remember { mutableStateOf<Book?>(null) }
    var renaming by remember { mutableStateOf<Book?>(null) }
    var deleting by remember { mutableStateOf<Book?>(null) }

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { uris ->
        vm.import(uris)
    }
    val pickPdf = { picker.launch(arrayOf("application/pdf")) }

    val shown = remember(books, query, vm.sort) {
        val q = query.trim()
        books.filter { q.isEmpty() || it.title.contains(q, ignoreCase = true) }
            .let { list ->
                when (vm.sort) {
                    SortOrder.RECENT -> list.sortedByDescending { maxOf(it.lastOpenedAt, it.addedAt) }
                    SortOrder.TITLE -> list.sortedBy { it.title.lowercase() }
                    SortOrder.ADDED -> list.sortedByDescending { it.addedAt }
                }
            }
    }
    val current = remember(books) { books.filter { it.lastOpenedAt > 0 && !it.isFinished }.maxByOrNull { it.lastOpenedAt } }

    val scroll = TopAppBarDefaults.pinnedScrollBehavior()

    Scaffold(
        modifier = Modifier.nestedScroll(scroll.nestedScrollConnection),
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            if (searching) {
                SearchBar(query, onQuery = { query = it }, onClose = { searching = false; query = "" })
            } else {
                TopAppBar(
                    title = { Text("Kitaab", style = MaterialTheme.typography.headlineSmall) },
                    actions = {
                        if (books.isNotEmpty()) {
                            IconButton(onClick = { searching = true }) { Icon(Icons.Filled.Search, "Search") }
                            SortButton(vm.sort, vm::updateSort)
                        }
                    },
                    scrollBehavior = scroll,
                    colors = TopAppBarDefaults.topAppBarColors(scrolledContainerColor = MaterialTheme.colorScheme.surfaceContainer),
                )
            }
        },
        floatingActionButton = {
            if (books.isNotEmpty()) {
                ExtendedFloatingActionButton(
                    onClick = pickPdf,
                    icon = { Icon(Icons.Filled.Add, null) },
                    text = { Text("Add PDF") },
                    containerColor = MaterialTheme.colorScheme.primary,
                    contentColor = MaterialTheme.colorScheme.onPrimary,
                )
            }
        },
    ) { pad ->
        Box(Modifier.fillMaxSize().padding(pad)) {
            if (books.isEmpty()) {
                EmptyShelf(onAdd = pickPdf, busy = vm.importing > 0)
            } else {
                LazyVerticalGrid(
                    columns = GridCells.Adaptive(minSize = 110.dp),
                    contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 96.dp),
                    horizontalArrangement = Arrangement.spacedBy(16.dp),
                    verticalArrangement = Arrangement.spacedBy(20.dp),
                    modifier = Modifier.fillMaxSize(),
                ) {
                    if (current != null && query.isBlank()) {
                        item(span = { GridItemSpan(maxLineSpan) }, key = "continue") {
                            ContinueCard(vm.library, current, onOpen = { vm.open(current.id) })
                        }
                    }
                    item(span = { GridItemSpan(maxLineSpan) }, key = "header") {
                        Text(
                            if (query.isBlank()) "Library · ${books.size}" else "${shown.size} found",
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.padding(top = 4.dp),
                        )
                    }
                    items(shown, key = { it.id }) { book ->
                        Box {
                            BookTile(
                                library = vm.library,
                                book = book,
                                onOpen = { vm.open(book.id) },
                                onLongPress = { menuFor = book },
                            )
                            DropdownMenu(expanded = menuFor?.id == book.id, onDismissRequest = { menuFor = null }) {
                                DropdownMenuItem(
                                    text = { Text("Rename") },
                                    leadingIcon = { Icon(Icons.Outlined.Edit, null) },
                                    onClick = { renaming = book; menuFor = null },
                                )
                                DropdownMenuItem(
                                    text = { Text("Remove from library") },
                                    leadingIcon = { Icon(Icons.Outlined.Delete, null) },
                                    onClick = { deleting = book; menuFor = null },
                                )
                            }
                        }
                    }
                    if (shown.isEmpty()) {
                        item(span = { GridItemSpan(maxLineSpan) }) {
                            Text(
                                "No book matches “$query”.",
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.padding(vertical = 24.dp),
                            )
                        }
                    }
                }
            }
            if (vm.importing > 0) {
                LinearProgressIndicator(Modifier.fillMaxWidth().align(Alignment.TopCenter))
            }
        }
    }

    renaming?.let { book ->
        RenameDialog(book, onDismiss = { renaming = null }, onSave = { vm.rename(book.id, it); renaming = null })
    }
    deleting?.let { book ->
        AlertDialog(
            onDismissRequest = { deleting = null },
            title = { Text("Remove this book?") },
            text = { Text("“${book.title}” and its bookmarks will be removed from Kitaab. The original PDF on your phone is not touched.") },
            confirmButton = { TextButton(onClick = { vm.delete(book.id); deleting = null }) { Text("Remove") } },
            dismissButton = { TextButton(onClick = { deleting = null }) { Text("Cancel") } },
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SearchBar(query: String, onQuery: (String) -> Unit, onClose: () -> Unit) {
    val focus = remember { FocusRequester() }
    LaunchedEffect(Unit) { focus.requestFocus() }
    TopAppBar(
        navigationIcon = { IconButton(onClick = onClose) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Close search") } },
        title = {
            TextField(
                value = query,
                onValueChange = onQuery,
                placeholder = { Text("Search your books") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = Color.Transparent,
                    unfocusedContainerColor = Color.Transparent,
                    focusedIndicatorColor = Color.Transparent,
                    unfocusedIndicatorColor = Color.Transparent,
                ),
                modifier = Modifier.fillMaxWidth().focusRequester(focus),
            )
        },
        actions = {
            if (query.isNotEmpty()) IconButton(onClick = { onQuery("") }) { Icon(Icons.Filled.Close, "Clear") }
        },
    )
}

@Composable
private fun SortButton(sort: SortOrder, onSort: (SortOrder) -> Unit) {
    var open by remember { mutableStateOf(false) }
    Box {
        IconButton(onClick = { open = true }) { Icon(Icons.AutoMirrored.Filled.Sort, "Sort") }
        DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            listOf(SortOrder.RECENT to "Recently read", SortOrder.TITLE to "Title", SortOrder.ADDED to "Recently added")
                .forEach { (order, label) ->
                    DropdownMenuItem(
                        text = { Text(label) },
                        trailingIcon = { if (order == sort) Icon(Icons.Filled.Check, null) },
                        onClick = { onSort(order); open = false },
                    )
                }
        }
    }
}

@Composable
private fun EmptyShelf(onAdd: () -> Unit, busy: Boolean) {
    Column(
        Modifier.fillMaxSize().padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Surface(shape = RoundedCornerShape(28.dp), color = MaterialTheme.colorScheme.secondaryContainer, modifier = Modifier.size(96.dp)) {
            Box(contentAlignment = Alignment.Center) {
                Icon(Icons.AutoMirrored.Filled.MenuBook, null, Modifier.size(48.dp), tint = MaterialTheme.colorScheme.onSecondaryContainer)
            }
        }
        Spacer(Modifier.height(24.dp))
        Text("Your shelf is empty", style = MaterialTheme.typography.headlineSmall, textAlign = TextAlign.Center)
        Spacer(Modifier.height(8.dp))
        Text(
            "Add a PDF from your phone. Kitaab keeps a copy, remembers your page, and opens it like a book.",
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(28.dp))
        Button(onClick = onAdd, enabled = !busy, contentPadding = PaddingValues(horizontal = 28.dp, vertical = 14.dp)) {
            Icon(Icons.Filled.Add, null)
            Spacer(Modifier.width(8.dp))
            Text(if (busy) "Adding…" else "Add PDF")
        }
    }
}

@Composable
private fun ContinueCard(library: Library, book: Book, onOpen: () -> Unit) {
    Card(
        onClick = onOpen,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh),
        shape = RoundedCornerShape(20.dp),
        modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
    ) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Cover(library, book, Modifier.width(76.dp))
            Spacer(Modifier.width(16.dp))
            Column(Modifier.weight(1f)) {
                Text("Continue reading", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.secondary)
                Spacer(Modifier.height(4.dp))
                Text(book.title, style = MaterialTheme.typography.titleMedium, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Spacer(Modifier.height(10.dp))
                ProgressLine(book.progress)
                Spacer(Modifier.height(6.dp))
                Text(
                    "Page ${book.lastPage + 1} of ${book.pageCount} · ${(book.progress * 100).toInt()}%",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Spacer(Modifier.height(12.dp))
                FilledTonalButton(onClick = onOpen, contentPadding = PaddingValues(horizontal = 20.dp, vertical = 8.dp)) {
                    Text("Resume")
                }
            }
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun BookTile(library: Library, book: Book, onOpen: () -> Unit, onLongPress: () -> Unit) {
    Column(
        Modifier
            .clip(RoundedCornerShape(8.dp))
            .combinedClickable(onClick = onOpen, onLongClick = onLongPress, onLongClickLabel = "Book options"),
    ) {
        Cover(library, book, Modifier.fillMaxWidth())
        Spacer(Modifier.height(8.dp))
        ProgressLine(book.progress, visible = book.lastOpenedAt > 0)
        Spacer(Modifier.height(6.dp))
        Text(book.title, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium, maxLines = 2, overflow = TextOverflow.Ellipsis)
        Text(
            when {
                book.lastOpenedAt == 0L -> "New · ${book.pageCount} pages"
                book.isFinished -> "Finished"
                else -> "${(book.progress * 100).toInt()}% · " +
                    DateUtils.getRelativeTimeSpanString(book.lastOpenedAt, System.currentTimeMillis(), DateUtils.MINUTE_IN_MILLIS)
            },
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun ProgressLine(progress: Float, visible: Boolean = true) {
    if (visible) {
        LinearProgressIndicator(
            progress = { progress },
            modifier = Modifier.fillMaxWidth().height(4.dp).clip(RoundedCornerShape(2.dp)),
            color = MaterialTheme.colorScheme.secondary,
            trackColor = MaterialTheme.colorScheme.outlineVariant,
            strokeCap = StrokeCap.Round,
            gapSize = 0.dp,
            drawStopIndicator = {},
        )
    } else {
        Spacer(Modifier.height(4.dp))
    }
}

private object CoverCache : LruCache<String, ImageBitmap>(48)

@Composable
private fun Cover(library: Library, book: Book, modifier: Modifier) {
    val image by produceState<ImageBitmap?>(CoverCache.get(book.id), book.id) {
        if (value == null) {
            value = withContext(Dispatchers.IO) {
                runCatching { BitmapFactory.decodeFile(library.coverFile(book.id).path)?.asImageBitmap() }.getOrNull()
            }?.also { CoverCache.put(book.id, it) }
        }
    }
    val shape = RoundedCornerShape(4.dp)
    Box(
        modifier
            .aspectRatio(0.7f)
            .shadow(4.dp, shape)
            .clip(shape)
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .border(0.5.dp, MaterialTheme.colorScheme.outlineVariant, shape),
        contentAlignment = Alignment.Center,
    ) {
        val img = image
        if (img != null) {
            Image(img, contentDescription = null, contentScale = ContentScale.Crop, alignment = Alignment.TopCenter, modifier = Modifier.fillMaxSize())
        } else {
            Text(
                book.title,
                style = MaterialTheme.typography.titleMedium,
                textAlign = TextAlign.Center,
                maxLines = 4,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.padding(10.dp),
            )
        }
    }
}

@Composable
private fun RenameDialog(book: Book, onDismiss: () -> Unit, onSave: (String) -> Unit) {
    var text by remember { mutableStateOf(book.title) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Rename book") },
        text = {
            OutlinedTextField(text, { text = it }, singleLine = true, label = { Text("Title") }, modifier = Modifier.fillMaxWidth())
        },
        confirmButton = { TextButton(onClick = { onSave(text) }, enabled = text.isNotBlank()) { Text("Save") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}
