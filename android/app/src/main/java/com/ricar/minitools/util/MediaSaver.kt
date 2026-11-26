package com.ricar.minitools.util

import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.provider.OpenableColumns
import java.io.File

/** 图片保存：Android 10+ 走 MediaStore（相册可见），更低版本落到应用私有外部目录。 */
object MediaSaver {
    private const val ALBUM = "MiniTools"

    fun saveBitmap(
        context: Context,
        bitmap: Bitmap,
        fileName: String,
        mimeType: String,
        quality: Int = 92,
    ): Uri? {
        val format = if (mimeType == "image/png") Bitmap.CompressFormat.PNG else Bitmap.CompressFormat.JPEG
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, fileName)
                put(MediaStore.Images.Media.MIME_TYPE, mimeType)
                put(MediaStore.Images.Media.RELATIVE_PATH, "${Environment.DIRECTORY_PICTURES}/$ALBUM")
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }
            val resolver = context.contentResolver
            val uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values) ?: return null
            resolver.openOutputStream(uri)?.use { out -> bitmap.compress(format, quality, out) }
            values.clear()
            values.put(MediaStore.Images.Media.IS_PENDING, 0)
            resolver.update(uri, values, null, null)
            uri
        } else {
            val dir = File(context.getExternalFilesDir(Environment.DIRECTORY_PICTURES), ALBUM).apply { mkdirs() }
            val file = File(dir, fileName)
            file.outputStream().use { out -> bitmap.compress(format, quality, out) }
            Uri.fromFile(file)
        }
    }

    fun outputLabel(context: Context): String =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            "相册 / Pictures/$ALBUM"
        } else {
            "Android/data/${context.packageName}/files/Pictures/$ALBUM"
        }

    fun queryDisplayName(context: Context, uri: Uri, fallback: String = "文件"): String {
        runCatching {
            context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)
                ?.use { cursor ->
                    if (cursor.moveToFirst()) {
                        val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                        if (index >= 0) {
                            val name = cursor.getString(index)
                            if (!name.isNullOrBlank()) return name
                        }
                    }
                }
        }
        return fallback
    }
}
