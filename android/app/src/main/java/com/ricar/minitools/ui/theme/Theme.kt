package com.ricar.minitools.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

val BrandBlue = Color(0xFF2563EB)
val BrandSky = Color(0xFF0EA5E9)
val BgGray = Color(0xFFF4F6F9)
val TextPrimary = Color(0xFF111827)
val TextSecondary = Color(0xFF6B7280)

private val LightColors = lightColorScheme(
    primary = BrandBlue,
    onPrimary = Color.White,
    secondary = BrandSky,
    background = BgGray,
    surface = Color.White,
    onBackground = TextPrimary,
    onSurface = TextPrimary,
)

@Composable
fun MiniToolsTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColors,
        typography = Typography(
            headlineSmall = TextStyle(fontSize = 22.sp, fontWeight = FontWeight.Bold),
            titleMedium = TextStyle(fontSize = 16.sp, fontWeight = FontWeight.SemiBold),
            bodyMedium = TextStyle(fontSize = 13.sp),
            bodySmall = TextStyle(fontSize = 12.sp),
            labelMedium = TextStyle(fontSize = 12.sp, fontWeight = FontWeight.Medium),
        ),
        shapes = Shapes(
            small = RoundedCornerShape(8.dp),
            medium = RoundedCornerShape(14.dp),
            large = RoundedCornerShape(18.dp),
        ),
        content = content,
    )
}
