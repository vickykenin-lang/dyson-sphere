package com.kitaab.reader.ui.reader

import android.graphics.Bitmap
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.calculatePan
import androidx.compose.foundation.gestures.calculateZoom
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.Stable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.input.pointer.positionChanged
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import com.kitaab.reader.pdf.PdfDocument
import kotlinx.coroutines.CancellationException

@Stable
class ZoomState {
    var scale by mutableFloatStateOf(1f)
    var offset by mutableStateOf(Offset.Zero)
    var contentSize by mutableStateOf(IntSize.Zero)
    val zoomed: Boolean get() = scale > 1.01f
}

/**
 * One PDF page. [fitScreen] centres the whole page on screen (page-flip mode);
 * otherwise the page fills the width (scroll mode). Pinch to zoom; when zoomed, one
 * finger pans. [onTap] gets the tap position as a fraction of the width.
 */
@Composable
fun PdfPage(
    doc: PdfDocument,
    index: Int,
    paper: Paper,
    fitScreen: Boolean,
    onTap: (Float) -> Unit,
    modifier: Modifier = Modifier,
) {
    val zoom = remember(index) { ZoomState() }
    val tap by rememberUpdatedState(onTap)
    val aspect = doc.pageSizes[index].aspect

    val gestures = Modifier
        .pointerInput(index) {
            detectTapGestures(onTap = { pos -> tap(pos.x / size.width) })
        }
        .pointerInput(zoom) {
            awaitEachGesture {
                awaitFirstDown(requireUnconsumed = false)
                do {
                    val event = awaitPointerEvent()
                    val fingers = event.changes.count { it.pressed }
                    if (fingers >= 2 || zoom.zoomed) {
                        val s = (zoom.scale * event.calculateZoom()).coerceIn(1f, 5f)
                        val c = zoom.contentSize
                        val maxX = ((c.width * s - size.width) / 2f).coerceAtLeast(0f)
                        val maxY = ((c.height * s - size.height) / 2f).coerceAtLeast(0f)
                        val p = zoom.offset + event.calculatePan()
                        zoom.scale = s
                        zoom.offset = Offset(p.x.coerceIn(-maxX, maxX), p.y.coerceIn(-maxY, maxY))
                        event.changes.forEach { if (it.positionChanged()) it.consume() }
                    }
                } while (event.changes.any { it.pressed })
                if (zoom.scale < 1.05f) {
                    zoom.scale = 1f
                    zoom.offset = Offset.Zero
                }
            }
        }

    if (fitScreen) {
        Box(modifier.fillMaxSize().then(gestures), contentAlignment = Alignment.Center) {
            PageImage(doc, index, paper, zoom, Modifier.aspectRatio(aspect))
        }
    } else {
        Box(modifier.fillMaxWidth().aspectRatio(aspect).then(gestures)) {
            PageImage(doc, index, paper, zoom, Modifier.fillMaxSize())
        }
    }
}

@Composable
private fun PageImage(doc: PdfDocument, index: Int, paper: Paper, zoom: ZoomState, modifier: Modifier) {
    var bitmap by remember(index) { mutableStateOf<Bitmap?>(null) }
    var failed by remember(index) { mutableStateOf(false) }
    val quality = when {
        zoom.scale > 2.6f -> 3
        zoom.scale > 1.3f -> 2
        else -> 1
    }
    val width = zoom.contentSize.width

    LaunchedEffect(index, width, quality) {
        if (width <= 0) return@LaunchedEffect
        try {
            doc.render(index, width * quality)?.let { bitmap = it }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Throwable) {
            if (bitmap == null) failed = true
        }
    }

    Box(
        modifier
            .onSizeChanged { zoom.contentSize = it }
            .graphicsLayer {
                scaleX = zoom.scale
                scaleY = zoom.scale
                translationX = zoom.offset.x
                translationY = zoom.offset.y
            }
            .background(paper.background),
        contentAlignment = Alignment.Center,
    ) {
        val bmp = bitmap
        when {
            bmp != null -> {
                val image = remember(bmp) { bmp.asImageBitmap() }
                Image(image, contentDescription = "Page ${index + 1}", colorFilter = paper.filter, contentScale = ContentScale.FillBounds, modifier = Modifier.fillMaxSize())
            }
            failed -> Text("Page ${index + 1} could not be shown", color = paper.muted)
            else -> CircularProgressIndicator(Modifier.size(28.dp), color = paper.muted, strokeWidth = 2.dp)
        }
    }
}
