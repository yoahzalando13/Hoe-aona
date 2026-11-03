package com.hoeaona.mobile.util;

import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.widget.Toast;
import com.hoeaona.mobile.R;

public final class Links {
    private Links() {}

    public static void open(Context context, String url) {
        if (url == null || url.isEmpty()) return;
        try {
            context.startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
        } catch (ActivityNotFoundException e) {
            Toast.makeText(context, R.string.error_no_app, Toast.LENGTH_SHORT).show();
        }
    }

    public static void share(Context context, String subject, String text) {
        Intent intent = new Intent(Intent.ACTION_SEND).setType("text/plain")
                .putExtra(Intent.EXTRA_SUBJECT, subject).putExtra(Intent.EXTRA_TEXT, text);
        context.startActivity(Intent.createChooser(intent, context.getString(R.string.share)));
    }
}
