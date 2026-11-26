package com.ricar.minitools.tools

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color as ComposeColor
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import com.ricar.minitools.ui.theme.TextSecondary
import com.ricar.minitools.util.MediaSaver
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlin.math.max

data class PdfOptions(
    val dpi: Int = 200,
    val png: Boolean = true,
    val zeroPad: Int = 3,
    val jpegQuality: Int = 92,
)

data class PdfOutcome(val name: String, val pages: Int, val ok: Boolean, val error: String? = null)

/** PDFium 之外的官方方案：Android 自带的 PdfRenderer，零依赖。 */
object PdfEngine {

    fun convert(
        context: Context,
        uri: Uri,
        options: PdfOptions,
        onPage: (done: Int, total: Int) -> Unit = { _, _ -> },
    ): PdfOutcome {
        val displayName = MediaSaver.queryDisplayName(context, uri, "文档.pdf")
        val baseName = displayName.substringBeforeLast('.', displayName)
        return try {
            val descriptor = context.contentResolver.openFileDescriptor(uri, "r")
                ?: return PdfOutcome(displayName, 0, false, "无法打开文件")
            descriptor.use { pfd ->
                val renderer = PdfRenderer(pfd)
                try {
                    val total = renderer.pageCount
                    if (total <= 0) return PdfOutcome(displayName, 0, false, "PDF 没有页面")
                    var done = 0
                    for (pageNumber in 1..total) {
                        val page = renderer.openPage(pageNumber - 1)
                        try {
                            val scale = options.dpi / 72f
                            val width = max(1, (page.width * scale).toInt())
                            val height = max(1, (page.height * scale).toInt())
                            val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                            Canvas(bitmap).drawColor(Color.WHITE)
                            page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)

                            val number = pageNumber.toString().padStart(max(0, options.zeroPad), '0')
                            val suffix = if (options.png) "png" else "jpg"
                            val mime = if (options.png) "image/png" else "image/jpeg"
                            MediaSaver.saveBitmap(
                                context,
                                bitmap,
                                "${baseName}_$number.$suffix",
                                mime,
                                options.jpegQuality,
                            )
                            bitmap.recycle()
                        } finally {
                            page.close()
                        }
                        done += 1
                        onPage(done, total)
                    }
                    PdfOutcome(displayName, done, true)
                } finally {
                    renderer.close()
                }
            }
        } catch (t: Throwable) {
            PdfOutcome(displayName, 0, false, t.message ?: t.javaClass.simpleName)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PdfToolScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var files by remember { mutableStateOf<List<Uri>>(emptyList()) }
    var dpi by remember { mutableIntStateOf(200) }
    var png by remember { mutableStateOf(true) }
    var zeroPad by remember { mutableStateOf(true) }
    var running by remember { mutableStateOf(false) }
    var progressText by remember { mutableStateOf("") }
    var message by remember { mutableStateOf("") }

    val picker = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenMultipleDocuments()
    ) { uris ->
        files = uris
        message = if (uris.isEmpty()) "" else "已选择 ${uris.size} 个文件"
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("PDF 转图片") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "返回")
                    }
                },
            )
        },
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item { Spacer(Modifier.height(4.dp)) }
            item {
                Text(
                    "每一页导出成图片，文件名：原文件名_页码",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary,
                )
            }
            item {
                OutlinedButton(
                    onClick = { picker.launch(arrayOf("application/pdf")) },
                    enabled = !running,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("选择 PDF 文件（可多选）") }
            }

            if (files.isNotEmpty()) {
                item {
                    Card(colors = CardDefaults.cardColors(containerColor = androidx.compose.ui.graphics.Color.White)) {
                        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text("已选 ${files.size} 个文件", style = MaterialTheme.typography.labelMedium)
                            files.take(6).forEach { uri ->
                                Text(
                                    MediaSaver.queryDisplayName(context, uri, "文件"),
                                    style = MaterialTheme.typography.bodySmall,
                                    color = TextSecondary,
                                )
                            }
                            if (files.size > 6) {
                                Text("… 另有 ${files.size - 6} 个", style = MaterialTheme.typography.bodySmall, color = TextSecondary)
                            }
                        }
                    }
                }
            }

            item {
                SectionCard("输出格式") {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilterChip(selected = png, onClick = { png = true }, label = { Text("PNG 无损") })
                        FilterChip(selected = !png, onClick = { png = false }, label = { Text("JPG 小体积") })
                    }
                }
            }

            item {
                SectionCard("分辨率") {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        listOf(150, 200, 300).forEach { value ->
                            FilterChip(
                                selected = dpi == value,
                                onClick = { dpi = value },
                                label = { Text("$value DPI") },
                            )
                        }
                    }
                }
            }

            item {
                SectionCard("页码补零（001 便于排序）") {
                    Switch(checked = zeroPad, onCheckedChange = { zeroPad = it }, enabled = !running)
                }
            }

            if (running) {
                item {
                    Column {
                        LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                        Spacer(Modifier.height(6.dp))
                        Text(progressText, style = MaterialTheme.typography.bodySmall, color = TextSecondary)
                    }
                }
            }

            item {
                Button(
                    onClick = {
                        if (files.isEmpty() || running) return@Button
                        running = true
                        message = "正在转换…"
                        progressText = ""
                        scope.launch {
                            var okFiles = 0
                            var failFiles = 0
                            var pages = 0
                            val options = PdfOptions(dpi = dpi, png = png, zeroPad = if (zeroPad) 3 else 0)
                            files.forEachIndexed { index, uri ->
                                val outcome = withContext(Dispatchers.IO) {
                                    PdfEngine.convert(context, uri, options) { done, total ->
                                        progressText = "第 ${index + 1}/${files.size} 个：$done/$total 页"
                                    }
                                }
                                if (outcome.ok) {
                                    okFiles += 1
                                    pages += outcome.pages
                                } else {
                                    failFiles += 1
                                }
                            }
                            running = false
                            message = buildString {
                                append("完成：$okFiles 个文件 / $pages 页")
                                if (failFiles > 0) append("，失败 $failFiles 个")
                                append("\n输出到 ${MediaSaver.outputLabel(context)}")
                            }
                        }
                    },
                    enabled = files.isNotEmpty() && !running,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text(if (running) "转换中…" else "开始转换") }
            }

            if (message.isNotEmpty()) {
                item {
                    Text(message, style = MaterialTheme.typography.bodySmall, color = TextSecondary)
                }
            }
            item { Spacer(Modifier.height(24.dp)) }
        }
    }
}

@Composable
internal fun SectionCard(title: String, content: @Composable () -> Unit) {
    Card(
        colors = CardDefaults.cardColors(containerColor = ComposeColor.White),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, style = MaterialTheme.typography.labelMedium, color = TextSecondary)
            Row(verticalAlignment = Alignment.CenterVertically) { content() }
        }
    }
}
