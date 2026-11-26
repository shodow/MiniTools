package com.ricar.minitools.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.ricar.minitools.tools.PdfToolScreen
import com.ricar.minitools.tools.WatermarkScreen
import com.ricar.minitools.ui.theme.BgGray

enum class Tool { Pdf2Img, Watermark }

@Composable
fun MiniToolsApp() {
    var current by remember { mutableStateOf<Tool?>(null) }

    BackHandler(enabled = current != null) { current = null }

    Surface(modifier = Modifier.fillMaxSize().background(BgGray)) {
        when (current) {
            null -> HomeScreen(onOpenTool = { current = it })
            Tool.Pdf2Img -> PdfToolScreen(onBack = { current = null })
            Tool.Watermark -> WatermarkScreen(onBack = { current = null })
        }
    }
}
