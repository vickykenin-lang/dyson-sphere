package com.kitaab.reader.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

val Ink = Color(0xFF1F3A5F)
val Amber = Color(0xFFE8A33D)

private val Light = lightColorScheme(
    primary = Ink,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFD6E3F5),
    onPrimaryContainer = Color(0xFF0B1E35),
    secondary = Color(0xFF8A5A14),
    secondaryContainer = Color(0xFFFBE3BC),
    onSecondaryContainer = Color(0xFF2C1A00),
    background = Color(0xFFFBF7F0),
    onBackground = Color(0xFF1C1B19),
    surface = Color(0xFFFBF7F0),
    onSurface = Color(0xFF1C1B19),
    surfaceVariant = Color(0xFFEDE6DA),
    onSurfaceVariant = Color(0xFF4D473D),
    surfaceContainer = Color(0xFFF3EDE3),
    surfaceContainerHigh = Color(0xFFEDE6DA),
    outline = Color(0xFF7E776B),
    outlineVariant = Color(0xFFD5CDBF),
)

private val Dark = darkColorScheme(
    primary = Color(0xFFA9C7EE),
    onPrimary = Color(0xFF0B2A4D),
    primaryContainer = Color(0xFF26446B),
    onPrimaryContainer = Color(0xFFD6E3F5),
    secondary = Color(0xFFF2C07A),
    secondaryContainer = Color(0xFF5C3F0E),
    onSecondaryContainer = Color(0xFFFBE3BC),
    background = Color(0xFF141311),
    onBackground = Color(0xFFE8E2D8),
    surface = Color(0xFF141311),
    onSurface = Color(0xFFE8E2D8),
    surfaceVariant = Color(0xFF2A2723),
    onSurfaceVariant = Color(0xFFCFC6B8),
    surfaceContainer = Color(0xFF1E1C19),
    surfaceContainerHigh = Color(0xFF282521),
    outline = Color(0xFF989083),
    outlineVariant = Color(0xFF3F3B35),
)

private val Serif = FontFamily.Serif

private val AppTypography = Typography().let { t ->
    t.copy(
        headlineMedium = t.headlineMedium.copy(fontFamily = Serif, fontWeight = FontWeight.SemiBold),
        headlineSmall = t.headlineSmall.copy(fontFamily = Serif, fontWeight = FontWeight.SemiBold),
        titleLarge = t.titleLarge.copy(fontFamily = Serif, fontWeight = FontWeight.SemiBold),
        titleMedium = TextStyle(fontFamily = Serif, fontWeight = FontWeight.SemiBold, fontSize = 17.sp, lineHeight = 22.sp),
    )
}

@Composable
fun KitaabTheme(dark: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (dark) Dark else Light, typography = AppTypography, content = content)
}
