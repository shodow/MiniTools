package com.ricar.minitools.tools

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color as AndroidColor
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.Typeface
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
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
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.ricar.minitools.ui.theme.TextSecondary
import com.ricar.minitools.util.MediaSaver
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlin.math.ceil
import kotlin.math.max
import kotlin.math.min

data class WatermarkOptions(
    val text: String = "",
    val opacity: Int = 75,
    val fontSize: Int = 20,
    val spacing: Int = 60,
    val angle: Int = 45,
    val color: Int = AndroidColor.WHITE,
    val outline: Boolean = true,
)

/** 平铺文字水印：与桌面版同一套参数（透明度 / 字号 / 间距 / 角度 / 描边）。 */
object WatermarkEngine {

    private const val MAX_SIDE = 4096

    fun decode(context: Context, uri: Uri): Bitmap? = runCatching {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        context.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
        var sample = 1
        while (max(bounds.outWidth, bounds.outHeight) / (sample * 2) >= MAX_SIDE) sample *= 2
        val options = BitmapFactory.Options().apply { inSampleSize = sample }
        context.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, options) }
    }.getOrNull()

    fun apply(source: Bitmap, options: WatermarkOptions): Bitmap {
        val output = source.copy(Bitmap.Config.ARGB_8888, true) ?: return source
        if (options.text.isBlank() || options.opacity <= 0) return output

        val stamp = buildStamp(options)
        if (stamp.width <= 0 || stamp.height <= 0) return output

        val canvas = Canvas(output)
        val stepX = stamp.width + options.spacing
        val stepY = stamp.height + options.spacing
        var y = -stamp.height
        while (y < output.height + stepY) {
            var x = -stamp.width
            while (x < output.width + stepX) {
                canvas.drawBitmap(stamp, x.toFloat(), y.toFloat(), null)
                x += stepX
            }
            y += stepY
        }
        stamp.recycle()
        return output
    }

    private fun buildStamp(options: WatermarkOptions): Bitmap {
        val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            textSize = options.fontSize.toFloat()
            color = options.color
            alpha = options.opacity * 255 / 100
            typeface = Typeface.SANS_SERIF
        }
        val lines = options.text.split("\n")
        val lineHeight = paint.descent() - paint.ascent()
        val widest = lines.maxOfOrNull { paint.measureText(it) } ?: 1f
        val stroke = if (options.outline) (if (options.fontSize >= 40) 2f else 1f) else 0f
        val padding = 4f + stroke

        val width = max(1, ceil(widest + padding * 2).toInt())
        val height = max(1, ceil(lineHeight * lines.size + padding * 2).toInt())
        val text = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(text)

        val strokePaint = Paint(paint).apply {
            style = Paint.Style.STROKE
            strokeWidth = stroke
            color = AndroidColor.BLACK
            alpha = min(220, (options.opacity * 255 / 100) * 9 / 10 + 15)
        }

        var baseline = padding - paint.ascent()
        for (line in lines) {
            if (options.outline) canvas.drawText(line, padding, baseline, strokePaint)
            canvas.drawText(line, padding, baseline, paint)
            baseline += lineHeight
        }

        if (options.angle % 360 == 0) return text
        val matrix = Matrix().apply { postRotate(-options.angle.toFloat()) }
        val rotated = Bitmap.createBitmap(text, 0, 0, text.width, text.height, matrix, true)
        if (rotated !== text) text.recycle()
        return rotated
    }
}

private data class ColorChoice(val label: String, val value: Color, val argb: Int)

private val COLOR_CHOICES = listOf(
    ColorChoice("白色", Color.White, AndroidColor.WHITE),
    ColorChoice("黑色", Color(0xFF111111), AndroidColor.rgb(17, 17, 17)),
    ColorChoice("浅灰", Color(0xFFD0D0D0), AndroidColor.rgb(208, 208, 208)),
    ColorChoice("深灰", Color(0xFF555555), AndroidColor.rgb(85, 85, 85)),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WatermarkScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var images by remember { mutableStateOf<List<Uri>>(emptyList()) }
    var text by remember { mutableStateOf("") }
    var opacity by remember { mutableIntStateOf(75) }
    var fontSize by remember { mutableIntStateOf(20) }
    var spacing by remember { mutableIntStateOf(60) }
    var angle by remember { mutableIntStateOf(45) }
    var colorChoice by remember { mutableStateOf(COLOR_CHOICES[0]) }
    var outline by remember { mutableStateOf(true) }
    var running by remember { mutableStateOf(false) }
    var progressText by remember { mutableStateOf("") }
    var message by remember { mutableStateOf("") }

    val picker = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenMultipleDocuments()
    ) { uris ->
        images = uris
        message = if (uris.isEmpty()) "" else "已选择 ${uris.size} 张图片"
    }

    val options = WatermarkOptions(
        text = text,
        opacity = opacity,
        fontSize = fontSize,
        spacing = spacing,
        angle = angle,
        color = colorChoice.argb,
        outline = outline,
    )

    val preview by produceState<Bitmap?>(
        initialValue = null,
        images.firstOrNull(),
        text,
        opacity,
        fontSize,
        spacing,
        angle,
        colorChoice,
        outline,
    ) {
        value = null
        val uri = images.firstOrNull() ?: return@produceState
        if (text.isBlank()) return@produceState
        value = withContext(Dispatchers.IO) {
            runCatching {
                val full = WatermarkEngine.decode(context, uri) ?: return@runCatching null
                val targetWidth = 720
                val factor = min(1f, targetWidth.toFloat() / full.width)
                val scaled = Bitmap.createScaledBitmap(
                    full,
                    max(1, (full.width * factor).toInt()),
                    max(1, (full.height * factor).toInt()),
                    true,
                )
                val previewOptions = options.copy(
                    fontSize = max(6, (fontSize * factor).toInt()),
                    spacing = max(2, (spacing * factor).toInt()),
                )
                WatermarkEngine.apply(scaled, previewOptions)
            }.getOrNull()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("图片加水印") },
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
            item {
                OutlinedButton(
                    onClick = { picker.launch(arrayOf("image/*")) },
                    enabled = !running,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("选择图片（可多选）") }
            }

            item {
                SectionCard("水印文字（支持中文）") {
                    OutlinedTextField(
                        value = text,
                        onValueChange = { text = it },
                        placeholder = { Text("例如：© 我的照片 2026") },
                        singleLine = false,
                        maxLines = 2,
                        enabled = !running,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }

            item {
                SectionCard("透明度 ${opacity}%") {
                    Slider(
                        value = opacity.toFloat(),
                        onValueChange = { opacity = it.toInt() },
                        valueRange = 0f..100f,
                        enabled = !running,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }

            item {
                SectionCard("文字大小 ${fontSize}px") {
                    Slider(
                        value = fontSize.toFloat(),
                        onValueChange = { fontSize = it.toInt() },
                        valueRange = 6f..120f,
                        enabled = !running,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }

            item {
                SectionCard("水印间距 ${spacing}px") {
                    Slider(
                        value = spacing.toFloat(),
                        onValueChange = { spacing = it.toInt() },
                        valueRange = 0f..300f,
                        enabled = !running,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }

            item {
                SectionCard("倾斜角度 ${angle}°") {
                    Slider(
                        value = angle.toFloat(),
                        onValueChange = { angle = it.toInt() },
                        valueRange = 0f..90f,
                        enabled = !running,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }

            item {
                SectionCard("文字颜色") {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        COLOR_CHOICES.forEach { choice ->
                            FilterChip(
                                selected = choice == colorChoice,
                                onClick = { colorChoice = choice },
                                label = { Text(choice.label) },
                            )
                        }
                    }
                }
            }

            item {
                SectionCard("描边（浅色背景也看得清）") {
                    Switch(checked = outline, onCheckedChange = { outline = it }, enabled = !running)
                }
            }

            if (preview != null) {
                item {
                    Card(colors = CardDefaults.cardColors(containerColor = Color.White)) {
                        Column(Modifier.padding(10.dp)) {
                            Text("预览（第一张图片，按比例缩放）", style = MaterialTheme.typography.labelMedium, color = TextSecondary)
                            Spacer(Modifier.height(6.dp))
                            Image(
                                bitmap = preview!!.asImageBitmap(),
                                contentDescription = "水印预览",
                                contentScale = ContentScale.Fit,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(180.dp),
                            )
                        }
                    }
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
                        if (images.isEmpty() || running) return@Button
                        if (text.isBlank()) {
                            message = "请先输入水印文字"
                            return@Button
                        }
                        running = true
                        message = "正在处理…"
                        progressText = ""
                        scope.launch {
                            var okCount = 0
                            var failCount = 0
                            images.forEachIndexed { index, uri ->
                                progressText = "第 ${index + 1}/${images.size} 张"
                                val result = withContext(Dispatchers.IO) {
                                    runCatching {
                                        val bitmap = WatermarkEngine.decode(context, uri)
                                            ?: return@runCatching false
                                        val marked = WatermarkEngine.apply(bitmap, options)
                                        val name = MediaSaver.queryDisplayName(context, uri, "图片.png")
                                        val base = name.substringBeforeLast('.', name)
                                        val suffix = if (name.lowercase().endsWith(".png")) "png" else "jpg"
                                        val mime = if (suffix == "png") "image/png" else "image/jpeg"
                                        val saved = MediaSaver.saveBitmap(
                                            context,
                                            marked,
                                            "${base}_watermark.$suffix",
                                            mime,
                                        )
                                        bitmap.recycle()
                                        saved != null
                                    }.getOrDefault(false)
                                }
                                if (result) okCount += 1 else failCount += 1
                            }
                            running = false
                            message = buildString {
                                append("完成：成功 $okCount 张")
                                if (failCount > 0) append("，失败 $failCount 张")
                                append("\n输出到 ${MediaSaver.outputLabel(context)}")
                            }
                        }
                    },
                    enabled = images.isNotEmpty() && !running,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text(if (running) "处理中…" else "开始加水印") }
            }

            if (message.isNotEmpty()) {
                item { Text(message, style = MaterialTheme.typography.bodySmall, color = TextSecondary) }
            }
            item { Spacer(Modifier.height(24.dp)) }
        }
    }
}
