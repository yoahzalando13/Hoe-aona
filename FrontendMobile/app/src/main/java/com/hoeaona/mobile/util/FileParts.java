package com.hoeaona.mobile.util;

import android.content.ContentResolver;
import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.provider.OpenableColumns;
import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.RequestBody;

import java.io.IOException;
import java.io.InputStream;
import java.io.ByteArrayOutputStream;

/** Conversion des fichiers choisis sur le téléphone en parties multipart. */
public final class FileParts {
    private FileParts() {}

    public static RequestBody text(String value) {
        return RequestBody.create(value == null ? "" : value, MediaType.parse("text/plain; charset=utf-8"));
    }

    public static String displayName(Context context, Uri uri) {
        try (Cursor cursor = context.getContentResolver().query(uri, null, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (index >= 0) return cursor.getString(index);
            }
        } catch (Exception ignored) {
            // nom par défaut ci-dessous
        }
        String last = uri.getLastPathSegment();
        return last != null ? last : "fichier";
    }

    public static MultipartBody.Part part(Context context, String field, Uri uri) throws IOException {
        ContentResolver resolver = context.getContentResolver();
        String mime = resolver.getType(uri);
        if (mime == null) mime = "application/octet-stream";
        byte[] bytes;
        try (InputStream in = resolver.openInputStream(uri)) {
            if (in == null) throw new IOException("Fichier illisible");
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buffer = new byte[16 * 1024];
            int n;
            while ((n = in.read(buffer)) > 0) out.write(buffer, 0, n);
            bytes = out.toByteArray();
        }
        return MultipartBody.Part.createFormData(field, displayName(context, uri),
                RequestBody.create(bytes, MediaType.parse(mime)));
    }
}
