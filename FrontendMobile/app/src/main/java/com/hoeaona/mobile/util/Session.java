package com.hoeaona.mobile.util;

import android.content.Context;
import com.hoeaona.mobile.model.User;

/** Rôle du compte connecté, mémorisé pour afficher tout de suite la bonne interface (rédaction ou lecteur). */
public final class Session {
    private static final String PREFS = "hoe_settings";
    private static final String KEY_ROLE = "role";

    private Session() {}

    public static void save(Context context, User user) {
        if (user == null) return;
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY_ROLE, user.role).apply();
    }

    public static boolean isReader(Context context) {
        return "reader".equals(context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_ROLE, null));
    }

    public static void clear(Context context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().remove(KEY_ROLE).apply();
    }
}
