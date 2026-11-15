package com.kitaab.reader.ui.reader

import android.app.Activity
import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.displayCutout
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.GenericShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.BookmarkBorder
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.TextFormat
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Slider
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.kitaab.reader.MainActivity
import com.kitaab.reader.data.Book
import com.kitaab.reader.data.PageMode
import com.kitaab.reader.data.ReaderSettings
import com.kitaab.reader.pdf.PdfDocument
import com.kitaab.reader.ui.AppViewModel
import com.kitaab.reader.ui.ReaderState
import com.kitaab.reader.ui.theme.Amber
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.distinctUntilChanged

/** A request to move to [page]; [animate] for one-page turns, instant for jumps. */
data class Jump(val page: Int, val animate: Boolean)

@Composable
fun ReaderScreen(vm: AppViewModel, bookId: String, snackbar: SnackbarHostState) {
    val books by vm.library.books.collectAsStateWithLifecycle()
    val book = books.firstOrNull { it.id == bookId }
    val paper = paperFor(vm.settings.theme)

    BackHandler { vm.closeReader() }

    Box(Modifier.fillMaxSize().background(paper.background)) {
        when (val state = vm.readerState) {
            is ReaderState.Loading -> CircularProgressIndicator(Modifier.align(Alignment.Center), color = paper.muted)
            is ReaderState.Error -> ErrorView(state.message, paper, onBack = vm::closeReader)
            is ReaderState.Ready -> if (book != null) {
                Reader(vm, book, state.doc, vm.settings, paper)
            }
        }
        SnackbarHost(snackbar, Modifier.align(Alignment.BottomCenter).navigationBarsPadding().padding(bottom = 80.dp))
    }
}

@OptIn(FlowPreview::class)
@Composable
private fun Reader(vm: AppViewModel, book: Book, doc: PdfDocument, settings: ReaderSettings, paper: Paper) {
    val count = doc.pageCount
    var page by rememberSaveable(book.id) { mutableIntStateOf(book.lastPage.coerceIn(0, count - 1)) }
    var chrome by rememberSaveable { mutableStateOf(false) }
    var sheet by remember { mutableStateOf<Sheet?>(null) }
    val jumps = remember { MutableSharedFlow<Jump>(extraBufferCapacity = 8) }

    val currentPage by rememberUpdatedState(page)
    fun goTo(target: Int, animate: Boolean) {
        val t = target.coerceIn(0, count - 1)
        if (t != currentPage) jumps.tryEmit(Jump(t, animate))
    }

    // Save the reading position shortly after the page settles, and when the reader closes.
    LaunchedEffect(book.id) {
        snapshotFlow { page }.distinctUntilChanged().debounce(500).collect { vm.savePosition(book.id, it) }
    }
    DisposableEffect(book.id) { onDispose { vm.savePosition(book.id, currentPage) } }

    SystemBars(visible = chrome || sheet != null, darkIcons = !paper.darkChrome)
    KeepScreenOn(settings.keepScreenOn)

    // Volume keys turn pages while the reader is open.
    val activity = LocalView.current.context as? MainActivity
    DisposableEffect(activity, settings.volumeKeysTurnPages, count) {
        if (settings.volumeKeysTurnPages) {
            activity?.volumeKeyHandler = { forward -> goTo(currentPage + if (forward) 1 else -1, animate = true); true }
        }
        onDispose { activity?.volumeKeyHandler = null }
    }

    val onTap: (Float) -> Unit = { x ->
        when {
            chrome -> { chrome = false }
            settings.mode == PageMode.FLIP && x < 0.3f -> goTo(currentPage - 1, animate = true)
            settings.mode == PageMode.FLIP && x > 0.7f -> goTo(currentPage + 1, animate = true)
            else -> { chrome = true }
        }
    }

    Box(Modifier.fillMaxSize()) {
        when (settings.mode) {
            PageMode.FLIP -> FlipPages(doc, startPage = page, paper = paper, jumps = jumps, onPage = { page = it }, onTap = onTap)
            PageMode.SCROLL -> ScrollPages(doc, startPage = page, paper = paper, jumps = jumps, onPage = { page = it }, onTap = onTap)
        }

        val marked = page in book.bookmarks
        if (marked) Ribbon(Modifier.align(Alignment.TopEnd).padding(end = 24.dp))

        // The quiet footer, like a Kindle's location line.
        AnimatedVisibility(!chrome, Modifier.align(Alignment.BottomCenter), enter = fadeIn(), exit = fadeOut()) {
            Row(
                Modifier.fillMaxWidth().navigationBarsPadding().padding(horizontal = 20.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text("Page ${page + 1} of $count", style = MaterialTheme.typography.labelSmall, color = paper.muted)
                Text("${((page + 1) * 100f / count).toInt()}%", style = MaterialTheme.typography.labelSmall, color = paper.muted)
            }
        }

        AnimatedVisibility(
            chrome,
            Modifier.align(Alignment.TopCenter),
            enter = slideInVertically { -it } + fadeIn(),
            exit = slideOutVertically { -it } + fadeOut(),
        ) {
            TopBar(
                title = book.title,
                paper = paper,
                marked = marked,
                onBack = vm::closeReader,
                onBookmark = { vm.toggleBookmark(book.id, page) },
                onContents = { sheet = Sheet.CONTENTS },
                onSettings = { sheet = Sheet.SETTINGS },
            )
        }

        AnimatedVisibility(
            chrome,
            Modifier.align(Alignment.BottomCenter),
            enter = slideInVertically { it } + fadeIn(),
            exit = slideOutVertically { it } + fadeOut(),
        ) {
            BottomBar(page, count, paper, onSeek = { goTo(it, animate = false) })
        }
    }

    when (sheet) {
        Sheet.SETTINGS -> SettingsSheet(settings, onChange = vm::updateSettings, onDismiss = { sheet = null })
        Sheet.CONTENTS -> ContentsSheet(
            book = book,
            current = page,
            onGo = { goTo(it, animate = false); sheet = null; chrome = false },
            onRemoveBookmark = { vm.toggleBookmark(book.id, it) },
            onDismiss = { sheet = null },
        )
        null -> {}
    }
}

private enum class Sheet { SETTINGS, CONTENTS }

@Composable
private fun FlipPages(
    doc: PdfDocument,
    startPage: Int,
    paper: Paper,
    jumps: MutableSharedFlow<Jump>,
    onPage: (Int) -> Unit,
    onTap: (Float) -> Unit,
) {
    val pager = rememberPagerState(initialPage = startPage) { doc.pageCount }
    LaunchedEffect(pager) { snapshotFlow { pager.currentPage }.collect { onPage(it) } }
    LaunchedEffect(pager) {
        jumps.collect { j -> if (j.animate) pager.animateScrollToPage(j.page) else pager.scrollToPage(j.page) }
    }
    HorizontalPager(
        state = pager,
        beyondViewportPageCount = 1,
        key = { it },
        modifier = Modifier
            .fillMaxSize()
            .windowInsetsPadding(WindowInsets.displayCutout)
            .padding(top = 6.dp, bottom = 26.dp),
    ) { index ->
        PdfPage(doc, index, paper, fitScreen = true, onTap = onTap)
    }
}

@Composable
private fun ScrollPages(
    doc: PdfDocument,
    startPage: Int,
    paper: Paper,
    jumps: MutableSharedFlow<Jump>,
    onPage: (Int) -> Unit,
    onTap: (Float) -> Unit,
) {
    val list = rememberLazyListState(initialFirstVisibleItemIndex = startPage)
    LaunchedEffect(list) {
        // The current page is the one crossing the middle of the screen.
        snapshotFlow {
            val info = list.layoutInfo
            val mid = (info.viewportStartOffset + info.viewportEndOffset) / 2
            info.visibleItemsInfo.firstOrNull { it.offset <= mid && it.offset + it.size > mid }?.index
                ?: list.firstVisibleItemIndex
        }.collect { onPage(it) }
    }
    LaunchedEffect(list) {
        jumps.collect { j -> if (j.animate) list.animateScrollToItem(j.page) else list.scrollToItem(j.page) }
    }
    LazyColumn(
        state = list,
        verticalArrangement = Arrangement.spacedBy(8.dp),
        contentPadding = PaddingValues(top = 8.dp, bottom = 48.dp),
        modifier = Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.displayCutout),
    ) {
        items(doc.pageCount, key = { it }) { index ->
            PdfPage(doc, index, paper, fitScreen = false, onTap = onTap)
        }
    }
}

@Composable
private fun TopBar(
    title: String,
    paper: Paper,
    marked: Boolean,
    onBack: () -> Unit,
    onBookmark: () -> Unit,
    onContents: () -> Unit,
    onSettings: () -> Unit,
) {
    Surface(color = paper.chrome, contentColor = paper.onChrome, shadowElevation = 2.dp) {
        Row(
            Modifier.fillMaxWidth().statusBarsPadding().height(56.dp).padding(horizontal = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back to library") }
            Text(
                title,
                style = MaterialTheme.typography.titleMedium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f).padding(horizontal = 4.dp),
            )
            IconButton(onClick = onContents) { Icon(Icons.AutoMirrored.Filled.List, "Go to page and bookmarks") }
            IconButton(onClick = onSettings) { Icon(Icons.Filled.TextFormat, "Reading settings") }
            IconButton(onClick = onBookmark) {
                if (marked) Icon(Icons.Filled.Bookmark, "Remove bookmark", tint = Amber)
                else Icon(Icons.Filled.BookmarkBorder, "Bookmark this page")
            }
        }
    }
}

@Composable
private fun BottomBar(page: Int, count: Int, paper: Paper, onSeek: (Int) -> Unit) {
    var dragging by remember { mutableStateOf(false) }
    var dragValue by remember { mutableFloatStateOf(page.toFloat()) }
    val value = if (dragging) dragValue else page.toFloat()
    val shown = value.toInt() + 1

    Surface(color = paper.chrome, contentColor = paper.onChrome, shadowElevation = 2.dp) {
        Column(Modifier.fillMaxWidth().navigationBarsPadding().padding(horizontal = 20.dp, vertical = 10.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("Page $shown of $count", style = MaterialTheme.typography.labelLarge)
                val left = count - shown
                Text(
                    if (left == 0) "Last page" else "$left page${if (left == 1) "" else "s"} left · ${(shown * 100f / count).toInt()}%",
                    style = MaterialTheme.typography.labelMedium,
                    color = paper.muted,
                )
            }
            if (count > 1) {
                Slider(
                    value = value,
                    onValueChange = { dragging = true; dragValue = it },
                    onValueChangeFinished = { dragging = false; onSeek(dragValue.toInt()) },
                    valueRange = 0f..(count - 1).toFloat(),
                    colors = SliderDefaults.colors(
                        thumbColor = Amber,
                        activeTrackColor = Amber,
                        inactiveTrackColor = paper.muted.copy(alpha = 0.35f),
                    ),
                )
            } else {
                Spacer(Modifier.height(12.dp))
            }
        }
    }
}

@Composable
private fun Ribbon(modifier: Modifier) {
    val shape = remember {
        GenericShape { size, _ ->
            moveTo(0f, 0f); lineTo(size.width, 0f); lineTo(size.width, size.height)
            lineTo(size.width / 2f, size.height * 0.78f); lineTo(0f, size.height); close()
        }
    }
    Box(modifier.size(width = 16.dp, height = 30.dp).background(Amber, shape))
}

@Composable
private fun ErrorView(message: String, paper: Paper, onBack: () -> Unit) {
    Column(
        Modifier.fillMaxSize().padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Icon(Icons.Filled.ErrorOutline, null, tint = paper.muted, modifier = Modifier.size(48.dp))
        Spacer(Modifier.height(16.dp))
        Text(message, color = paper.onChrome, style = MaterialTheme.typography.titleMedium)
        Spacer(Modifier.height(24.dp))
        Button(onClick = onBack) { Text("Back to library") }
    }
}

@Composable
private fun SystemBars(visible: Boolean, darkIcons: Boolean) {
    val view = LocalView.current
    val window = (view.context as? Activity)?.window ?: return
    val controller = remember(window) { WindowCompat.getInsetsController(window, view) }
    DisposableEffect(visible, darkIcons) {
        controller.systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        controller.isAppearanceLightStatusBars = darkIcons
        controller.isAppearanceLightNavigationBars = darkIcons
        if (visible) controller.show(WindowInsetsCompat.Type.systemBars())
        else controller.hide(WindowInsetsCompat.Type.systemBars())
        onDispose { }
    }
    DisposableEffect(controller) {
        onDispose {
            controller.show(WindowInsetsCompat.Type.systemBars())
            val night = (view.resources.configuration.uiMode and android.content.res.Configuration.UI_MODE_NIGHT_MASK) ==
                android.content.res.Configuration.UI_MODE_NIGHT_YES
            controller.isAppearanceLightStatusBars = !night
            controller.isAppearanceLightNavigationBars = !night
        }
    }
}

@Composable
private fun KeepScreenOn(on: Boolean) {
    val view = LocalView.current
    DisposableEffect(on) {
        view.keepScreenOn = on
        onDispose { view.keepScreenOn = false }
    }
}

