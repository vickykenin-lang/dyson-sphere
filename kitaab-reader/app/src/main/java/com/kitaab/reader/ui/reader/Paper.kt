package com.kitaab.reader.ui.reader

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.ColorMatrix
import com.kitaab.reader.data.PaperTheme

/** How a reading theme looks: the colour around the page, and the filter applied to the page itself. */
data class Paper(
    val background: Color,
    val chrome: Color,
    val onChrome: Color,
    val muted: Color,
    val filter: ColorFilter?,
    val darkChrome: Boolean,
)

/**
 * Maps every channel linearly so that black ink becomes [ink] and white paper becomes [paper].
 * PDF pages render as black on white, so this recolours the whole page in one GPU pass.
 */
private fun remap(ink: Color, paper: Color): ColorFilter {
    fun row(i: Float, p: Float, ch: Int): FloatArray {
        val r = FloatArray(5)
        r[ch] = (p - i)          // slope: 0 -> ink, 1 -> paper
        r[4] = i * 255f          // offset in 0..255
        return r
    }
    val m = row(ink.red, paper.red, 0) + row(ink.green, paper.green, 1) + row(ink.blue, paper.blue, 2) +
        floatArrayOf(0f, 0f, 0f, 1f, 0f)
    return ColorFilter.colorMatrix(ColorMatrix(m))
}

fun paperFor(theme: PaperTheme): Paper = when (theme) {
    PaperTheme.DAY -> Paper(
        background = Color(0xFFFFFFFF),
        chrome = Color(0xFFF7F5F1),
        onChrome = Color(0xFF1C1B19),
        muted = Color(0xFF8A857C),
        filter = null,
        darkChrome = false,
    )
    PaperTheme.SEPIA -> Paper(
        background = Color(0xFFF5ECD7),
        chrome = Color(0xFFEDE1C6),
        onChrome = Color(0xFF3B2B19),
        muted = Color(0xFF8C7655),
        filter = remap(ink = Color(0xFF3B2B19), paper = Color(0xFFF5ECD7)),
        darkChrome = false,
    )
    PaperTheme.NIGHT -> Paper(
        background = Color(0xFF121212),
        chrome = Color(0xFF1E1E1E),
        onChrome = Color(0xFFE2DED6),
        muted = Color(0xFF8E8A83),
        filter = remap(ink = Color(0xFFD0CCC4), paper = Color(0xFF121212)),
        darkChrome = true,
    )
}
