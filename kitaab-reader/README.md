# Kitaab Reader

A Kindle-style Android app for reading your own PDFs like books.

## What it does

- **Library**: add PDFs from your phone (one or many at once). Each book shows its cover, how far you have read, and when you last read it. Search, sort, rename and remove books.
- **Continue reading**: the home screen opens with the book you were reading, at the page you left.
- **Reading**: swipe or tap the left/right edge to turn pages, or switch to scrolling down. Tap the middle for the menu. Pinch to zoom.
- **Themes**: Day, Sepia and Night (recolours the page itself, easy on the eyes at night).
- **Bookmarks** and **go to page**, plus a page slider.
- Volume buttons turn pages, the screen stays on while reading, and the system bars hide for full-screen reading.
- "Open with" and "Share" from a file manager, browser or WhatsApp add the PDF straight to the library.

Kitaab keeps its own copy of every PDF, so the book stays readable even if the original file is moved or deleted.
Password-protected PDFs cannot be opened (Android's built-in PDF engine does not support them).

## Get the APK

GitHub Actions builds it on every push that touches this folder:
**Actions → Kitaab Reader APK → the latest run → Artifacts → Kitaab-Reader-apk**. Unzip it to get `Kitaab-Reader.apk`.

## Install on the phone

1. Copy `Kitaab-Reader.apk` to the phone and open it.
2. If Android asks, allow "Install unknown apps" for the app you opened it from (Files, Chrome, etc.).
3. Tap **Install**. Kitaab appears with the other apps.

Needs Android 8.0 or newer.

## Build it yourself

```
cd kitaab-reader
./gradlew assembleRelease      # app/build/outputs/apk/release/app-release.apk
```

Needs JDK 17 and the Android SDK (platform 35). `app/sideload.keystore` is a fixed signing key used only so
new builds install over old ones without losing the library. It is not a Play Store key.
