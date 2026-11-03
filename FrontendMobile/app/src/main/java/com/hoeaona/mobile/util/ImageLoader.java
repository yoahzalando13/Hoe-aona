package com.hoeaona.mobile.util;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Handler;
import android.os.Looper;
import android.util.LruCache;
import android.view.View;
import android.widget.ImageView;
import com.hoeaona.mobile.api.ApiClient;
import okhttp3.Request;
import okhttp3.Response;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Images protégées par la session (publications, photos de constat) : chargées avec le client authentifié. */
public final class ImageLoader {
    private static final LruCache<String, Bitmap> CACHE = new LruCache<String, Bitmap>(16 * 1024 * 1024) {
        @Override
        protected int sizeOf(String key, Bitmap value) {
            return value.getByteCount();
        }
    };
    private static final ExecutorService EXECUTOR = Executors.newFixedThreadPool(3);
    private static final Handler MAIN = new Handler(Looper.getMainLooper());

    private ImageLoader() {}

    public static void load(ImageView view, String path) {
        if (path == null) {
            view.setTag(null);
            view.setImageDrawable(null);
            view.setVisibility(View.GONE);
            return;
        }
        String url = ApiClient.absolute(path);
        view.setTag(url);
        view.setVisibility(View.VISIBLE);
        Bitmap cached = CACHE.get(url);
        if (cached != null) {
            view.setImageBitmap(cached);
            return;
        }
        view.setImageDrawable(null);
        EXECUTOR.execute(() -> {
            Bitmap bitmap = fetch(url);
            if (bitmap != null) CACHE.put(url, bitmap);
            MAIN.post(() -> {
                if (url.equals(view.getTag())) {
                    if (bitmap != null) view.setImageBitmap(bitmap);
                    else view.setVisibility(View.GONE);
                }
            });
        });
    }

    private static Bitmap fetch(String url) {
        try (Response response = ApiClient.getHttpClient().newCall(new Request.Builder().url(url).build()).execute()) {
            if (!response.isSuccessful() || response.body() == null) return null;
            byte[] bytes = response.body().bytes();
            BitmapFactory.Options bounds = new BitmapFactory.Options();
            bounds.inJustDecodeBounds = true;
            BitmapFactory.decodeByteArray(bytes, 0, bytes.length, bounds);
            BitmapFactory.Options options = new BitmapFactory.Options();
            options.inSampleSize = 1;
            while (Math.max(bounds.outWidth, bounds.outHeight) / options.inSampleSize > 1600) {
                options.inSampleSize *= 2;
            }
            return BitmapFactory.decodeByteArray(bytes, 0, bytes.length, options);
        } catch (Exception e) {
            return null;
        }
    }
}
