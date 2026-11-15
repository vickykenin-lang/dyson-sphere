package com.kitaab.reader

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.KeyEvent
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.material3.SnackbarHostState
import androidx.compose.runtime.remember
import com.kitaab.reader.ui.AppViewModel
import com.kitaab.reader.ui.Screen
import com.kitaab.reader.ui.library.LibraryScreen
import com.kitaab.reader.ui.reader.ReaderScreen
import com.kitaab.reader.ui.theme.KitaabTheme

class MainActivity : ComponentActivity() {

    private val vm: AppViewModel by viewModels()

    /** Set by the reader while it is on screen: returns true when it used the key. */
    var volumeKeyHandler by mutableStateOf<((Boolean) -> Boolean)?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        if (savedInstanceState == null) handleIncoming(intent)

        setContent {
            KitaabTheme {
                val snackbar = remember { SnackbarHostState() }
                LaunchedEffect(Unit) {
                    vm.messages.collect { snackbar.showSnackbar(it) }
                }
                AnimatedContent(
                    targetState = vm.screen,
                    transitionSpec = { fadeIn() togetherWith fadeOut() },
                    contentKey = { it::class },
                    label = "screen",
                ) { screen ->
                    when (screen) {
                        is Screen.Library -> LibraryScreen(vm, snackbar)
                        is Screen.Reader -> ReaderScreen(vm, screen.bookId, snackbar)
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleIncoming(intent)
    }

    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        val handler = volumeKeyHandler
        if (handler != null && (event.keyCode == KeyEvent.KEYCODE_VOLUME_DOWN || event.keyCode == KeyEvent.KEYCODE_VOLUME_UP)) {
            if (event.action == KeyEvent.ACTION_DOWN) {
                if (handler(event.keyCode == KeyEvent.KEYCODE_VOLUME_DOWN)) return true
            } else if (event.action == KeyEvent.ACTION_UP) {
                return true
            }
        }
        return super.dispatchKeyEvent(event)
    }

    private fun handleIncoming(intent: Intent?) {
        intent ?: return
        val uris: List<Uri> = when (intent.action) {
            Intent.ACTION_VIEW -> listOfNotNull(intent.data)
            Intent.ACTION_SEND -> listOfNotNull(intent.parcelable(Intent.EXTRA_STREAM))
            Intent.ACTION_SEND_MULTIPLE -> intent.parcelableList(Intent.EXTRA_STREAM)
            else -> emptyList()
        }
        if (uris.isNotEmpty()) vm.import(uris, openWhenSingle = true)
    }

    @Suppress("DEPRECATION")
    private fun Intent.parcelable(key: String): Uri? =
        if (Build.VERSION.SDK_INT >= 33) getParcelableExtra(key, Uri::class.java) else getParcelableExtra(key)

    @Suppress("DEPRECATION")
    private fun Intent.parcelableList(key: String): List<Uri> =
        (if (Build.VERSION.SDK_INT >= 33) getParcelableArrayListExtra(key, Uri::class.java)
        else getParcelableArrayListExtra(key)) ?: emptyList()
}
