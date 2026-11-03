package com.hoeaona.mobile.api;

import android.content.Context;
import android.content.SharedPreferences;
import okhttp3.Cookie;
import okhttp3.CookieJar;
import okhttp3.HttpUrl;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Garde le cookie de session entre deux lancements de l'application. */
public class PersistentCookieJar implements CookieJar {
    private static final String PREFS = "hoe_cookies";
    private final SharedPreferences prefs;

    public PersistentCookieJar(Context context) {
        prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    @Override
    public synchronized void saveFromResponse(HttpUrl url, List<Cookie> cookies) {
        Set<String> stored = new HashSet<>(prefs.getStringSet(url.host(), new HashSet<>()));
        for (Cookie cookie : cookies) {
            stored.removeIf(s -> s.startsWith(cookie.name() + "="));
            if (cookie.expiresAt() > System.currentTimeMillis()) {
                stored.add(cookie.toString());
            }
        }
        prefs.edit().putStringSet(url.host(), stored).apply();
    }

    @Override
    public synchronized List<Cookie> loadForRequest(HttpUrl url) {
        List<Cookie> out = new ArrayList<>();
        for (String raw : prefs.getStringSet(url.host(), new HashSet<>())) {
            Cookie cookie = Cookie.parse(url, raw);
            if (cookie != null && cookie.expiresAt() > System.currentTimeMillis()) {
                out.add(cookie);
            }
        }
        return out;
    }

    public synchronized void clear() {
        prefs.edit().clear().apply();
    }
}
