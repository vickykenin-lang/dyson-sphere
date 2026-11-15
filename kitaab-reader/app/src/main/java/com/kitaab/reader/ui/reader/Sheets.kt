package com.kitaab.reader.ui.reader

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.kitaab.reader.data.Book
import com.kitaab.reader.data.PageMode
import com.kitaab.reader.data.PaperTheme
import com.kitaab.reader.data.ReaderSettings
import com.kitaab.reader.ui.theme.Amber

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsSheet(settings: ReaderSettings, onChange: (ReaderSettings) -> Unit, onDismiss: () -> Unit) {
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 24.dp).padding(bottom = 24.dp).navigationBarsPadding()) {
            Text("Theme", style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                listOf(PaperTheme.DAY to "Day", PaperTheme.SEPIA to "Sepia", PaperTheme.NIGHT to "Night").forEach { (t, label) ->
                    ThemeSwatch(t, label, selected = settings.theme == t, Modifier.weight(1f)) { onChange(settings.copy(theme = t)) }
                }
            }

            Spacer(Modifier.height(24.dp))
            Text("Page turning", style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(12.dp))
            SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                val modes = listOf(PageMode.FLIP to "Swipe pages", PageMode.SCROLL to "Scroll down")
                modes.forEachIndexed { i, (m, label) ->
                    SegmentedButton(
                        selected = settings.mode == m,
                        onClick = { onChange(settings.copy(mode = m)) },
                        shape = SegmentedButtonDefaults.itemShape(i, modes.size),
                    ) { Text(label) }
                }
            }

            Spacer(Modifier.height(16.dp))
            SwitchRow("Volume buttons turn pages", settings.volumeKeysTurnPages) { onChange(settings.copy(volumeKeysTurnPages = it)) }
            SwitchRow("Keep screen on while reading", settings.keepScreenOn) { onChange(settings.copy(keepScreenOn = it)) }

            Spacer(Modifier.height(8.dp))
            Text(
                "Tip: tap the left or right edge to turn a page, the middle for this menu. Pinch to zoom.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun ThemeSwatch(theme: PaperTheme, label: String, selected: Boolean, modifier: Modifier, onClick: () -> Unit) {
    val p = paperFor(theme)
    val shape = RoundedCornerShape(14.dp)
    Column(
        modifier
            .clip(shape)
            .background(p.background)
            .border(
                if (selected) BorderStroke(2.5.dp, Amber) else BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                shape,
            )
            .clickable(onClick = onClick)
            .padding(vertical = 14.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("Aa", color = p.onChrome, fontFamily = FontFamily.Serif, fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
        Spacer(Modifier.height(2.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (selected) {
                Icon(Icons.Filled.Check, null, tint = p.onChrome, modifier = Modifier.size(14.dp))
                Spacer(Modifier.width(4.dp))
            }
            Text(label, color = p.onChrome, style = MaterialTheme.typography.labelMedium)
        }
    }
}

@Composable
private fun SwitchRow(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(
        Modifier.fillMaxWidth().clickable { onChange(!checked) }.padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
        Switch(checked = checked, onCheckedChange = onChange)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ContentsSheet(
    book: Book,
    current: Int,
    onGo: (Int) -> Unit,
    onRemoveBookmark: (Int) -> Unit,
    onDismiss: () -> Unit,
) {
    var input by remember { mutableStateOf("") }
    val target = input.toIntOrNull()
    val valid = target != null && target in 1..book.pageCount
    val go = { if (valid) onGo(target!! - 1) }

    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 24.dp).navigationBarsPadding()) {
            Text(book.title, style = MaterialTheme.typography.titleMedium, maxLines = 2)
            Text(
                "Page ${current + 1} of ${book.pageCount}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(16.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    value = input,
                    onValueChange = { v -> input = v.filter { it.isDigit() }.take(6) },
                    label = { Text("Go to page") },
                    placeholder = { Text("1 – ${book.pageCount}") },
                    singleLine = true,
                    isError = input.isNotEmpty() && !valid,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number, imeAction = ImeAction.Go),
                    keyboardActions = KeyboardActions(onGo = { go() }),
                    modifier = Modifier.weight(1f),
                )
                Spacer(Modifier.width(12.dp))
                FilledTonalButton(onClick = go, enabled = valid) { Text("Go") }
            }

            Spacer(Modifier.height(16.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilledTonalButton(onClick = { onGo(0) }, modifier = Modifier.weight(1f)) { Text("Beginning") }
                FilledTonalButton(onClick = { onGo(book.pageCount - 1) }, modifier = Modifier.weight(1f)) { Text("End") }
            }

            Spacer(Modifier.height(24.dp))
            Text("Bookmarks", style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(4.dp))
            if (book.bookmarks.isEmpty()) {
                Text(
                    "No bookmarks yet. Tap the bookmark icon at the top while reading to save a page here.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(vertical = 12.dp),
                )
            } else {
                LazyColumn(Modifier.heightIn(max = 320.dp)) {
                    items(book.bookmarks, key = { it }) { p ->
                        Row(
                            Modifier.fillMaxWidth().clickable { onGo(p) }.padding(vertical = 4.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Box(Modifier.size(32.dp).clip(CircleShape).background(Amber.copy(alpha = 0.18f)), contentAlignment = Alignment.Center) {
                                Icon(Icons.Filled.Bookmark, null, tint = Amber, modifier = Modifier.size(18.dp))
                            }
                            Spacer(Modifier.width(14.dp))
                            Text(
                                "Page ${p + 1}" + if (p == current) "  ·  you are here" else "",
                                style = MaterialTheme.typography.bodyLarge,
                                modifier = Modifier.weight(1f),
                            )
                            IconButton(onClick = { onRemoveBookmark(p) }) { Icon(Icons.Outlined.Close, "Remove bookmark") }
                        }
                        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                    }
                }
            }
            Spacer(Modifier.height(24.dp))
        }
    }
}
