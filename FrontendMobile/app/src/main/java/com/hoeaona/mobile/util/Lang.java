package com.hoeaona.mobile.util;

import androidx.appcompat.app.AppCompatDelegate;
import androidx.core.os.LocaleListCompat;

/** Langue de l'interface : malagasy, français ou anglais (mémorisée par AppCompat). */
public final class Lang {
    public static final String[] CODES = {"mg", "fr", "en"};

    private Lang() {}

    public static void set(String code) {
        AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(code));
    }

    public static String current() {
        LocaleListCompat locales = AppCompatDelegate.getApplicationLocales();
        String tag = locales.isEmpty() ? java.util.Locale.getDefault().getLanguage() : locales.get(0).getLanguage();
        for (String code : CODES) if (code.equals(tag)) return code;
        return "fr";
    }
}
