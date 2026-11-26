package com.ricar.minitools.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ricar.minitools.ui.theme.BgGray
import com.ricar.minitools.ui.theme.BrandBlue
import com.ricar.minitools.ui.theme.BrandSky
import com.ricar.minitools.ui.theme.TextSecondary

private data class ToolEntry(
    val tool: Tool,
    val badge: String,
    val title: String,
    val summary: String,
    val accent: Color,
)

private val ENTRIES = listOf(
    ToolEntry(
        tool = Tool.Pdf2Img,
        badge = "PDF",
        title = "PDF 转图片",
        summary = "把 PDF 的每一页导出成 PNG / JPG，支持批量",
        accent = BrandBlue,
    ),
    ToolEntry(
        tool = Tool.Watermark,
        badge = "水印",
        title = "图片加水印",
        summary = "给 PNG / JPG 平铺文字水印，支持中文",
        accent = BrandSky,
    ),
)

@Composable
fun HomeScreen(onOpenTool: (Tool) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgGray)
            .padding(horizontal = 20.dp, vertical = 16.dp),
    ) {
        Text("MiniTools 工具箱", style = MaterialTheme.typography.headlineSmall)
        Text(
            "选一张卡片，开始使用对应的小工具",
            style = MaterialTheme.typography.bodyMedium,
            color = TextSecondary,
        )
        Spacer(Modifier.height(18.dp))

        LazyVerticalGrid(
            columns = GridCells.Adaptive(minSize = 156.dp),
            horizontalArrangement = Arrangement.spacedBy(14.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
            modifier = Modifier.weight(1f),
        ) {
            items(ENTRIES) { entry ->
                ToolCard(entry) { onOpenTool(entry.tool) }
            }
        }

        Text(
            "MiniTools v2.0.0 · 本地处理，不联网",
            style = MaterialTheme.typography.bodySmall,
            color = TextSecondary,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 12.dp),
        )
    }
}

@Composable
private fun ToolCard(entry: ToolEntry, onClick: () -> Unit) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Badge(entry.badge, entry.accent)
            Spacer(Modifier.height(12.dp))
            Text(
                entry.title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                entry.summary,
                style = MaterialTheme.typography.bodySmall,
                color = TextSecondary,
                lineHeight = 17.sp,
            )
        }
    }
}

@Composable
private fun Badge(text: String, accent: Color) {
    Box(
        modifier = Modifier
            .size(48.dp)
            .background(
                brush = Brush.linearGradient(listOf(accent.copy(alpha = 0.95f), accent)),
                shape = RoundedCornerShape(13.dp),
            ),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text,
            color = Color.White,
            fontSize = if (text.length > 2) 14.sp else 15.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}
