package com.ricar.minitools

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.ricar.minitools.ui.MiniToolsApp
import com.ricar.minitools.ui.theme.MiniToolsTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MiniToolsTheme {
                MiniToolsApp()
            }
        }
    }
}
