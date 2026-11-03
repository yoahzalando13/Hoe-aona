package com.hoeaona.mobile.util;

import android.content.Context;
import android.graphics.drawable.GradientDrawable;
import android.text.SpannableString;
import android.text.Spanned;
import android.text.style.ForegroundColorSpan;
import android.text.style.RelativeSizeSpan;
import android.widget.TextView;
import androidx.annotation.ColorRes;
import androidx.core.content.ContextCompat;
import com.hoeaona.mobile.R;

import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.format.FormatStyle;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/** Libellés et formats affichés : scores sur 10, dates locales, verdicts et états traduits. */
public final class Format {
    private Format() {}

    public static String score(Double value) {
        return value == null ? "–" : String.format(Locale.getDefault(), "%.1f/10", value);
    }

    /** « 6,4/10 » avec « /10 » plus petit et plus pâle : le chiffre seul porte l'information. */
    public static CharSequence scoreSpan(Context c, Double value) {
        if (value == null) return "–";
        String number = String.format(Locale.getDefault(), "%.1f", value);
        SpannableString out = new SpannableString(number + "/10");
        int start = number.length();
        out.setSpan(new RelativeSizeSpan(0.42f), start, out.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        out.setSpan(new ForegroundColorSpan(ContextCompat.getColor(c, R.color.gray_text)), start, out.length(),
                Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        return out;
    }

    /** Verdict en « tampon » : capitales et filet de la couleur du verdict. */
    public static void stamp(TextView view, @ColorRes int color) {
        int c = ContextCompat.getColor(view.getContext(), color);
        float d = view.getResources().getDisplayMetrics().density;
        GradientDrawable bg = new GradientDrawable();
        bg.setCornerRadius(3 * d);
        bg.setStroke((int) Math.max(1, d), c);
        view.setBackground(bg);
        view.setTextColor(c);
        view.setAllCaps(true);
        view.setLetterSpacing(0.06f);
        view.setPadding((int) (8 * d), (int) (2 * d), (int) (8 * d), (int) (2 * d));
    }

    public static String date(String iso) {
        if (iso == null) return "";
        try {
            return OffsetDateTime.parse(iso).atZoneSameInstant(ZoneId.systemDefault())
                    .format(DateTimeFormatter.ofLocalizedDateTime(FormatStyle.SHORT).withLocale(Locale.getDefault()));
        } catch (Exception e) {
            return iso.length() >= 10 ? iso.substring(0, 10) : iso;
        }
    }

    public static String number(Double value) {
        if (value == null) return "–";
        double abs = Math.abs(value);
        if (abs >= 1e9) return String.format(Locale.getDefault(), "%.2f G", value / 1e9);
        if (abs >= 1e6) return String.format(Locale.getDefault(), "%.2f M", value / 1e6);
        return String.format(Locale.getDefault(), abs >= 100 ? "%,.0f" : "%.2f", value);
    }

    private static String label(Context c, Map<String, Integer> labels, String key) {
        if (key == null) return "";
        Integer id = labels.get(key);
        return id != null ? c.getString(id) : key;
    }

    private static Map<String, Integer> map(Object... pairs) {
        Map<String, Integer> m = new HashMap<>();
        for (int i = 0; i < pairs.length; i += 2) m.put((String) pairs[i], (Integer) pairs[i + 1]);
        return m;
    }

    private static final Map<String, Integer> VERDICTS = map(
            "fiable", R.string.verdict_fiable, "plutot_fiable", R.string.verdict_plutot_fiable,
            "a_verifier", R.string.verdict_a_verifier, "douteux", R.string.verdict_douteux);
    private static final Map<String, Integer> WORKFLOWS = map(
            "a_traiter", R.string.workflow_a_traiter, "en_revue", R.string.workflow_en_revue,
            "valide", R.string.workflow_valide, "publie", R.string.workflow_publie, "archive", R.string.workflow_archive);
    private static final Map<String, Integer> STATUSES = map(
            "pending", R.string.status_pending, "running", R.string.status_running,
            "done", R.string.status_done, "error", R.string.status_error);
    private static final Map<String, Integer> VERIFICATION_STATUSES = map(
            "open", R.string.verif_status_open, "accepted", R.string.verif_status_accepted,
            "completed", R.string.verif_status_completed, "cancelled", R.string.verif_status_cancelled,
            "expired", R.string.verif_status_expired);
    private static final Map<String, Integer> OUTCOMES = map(
            "correct", R.string.verif_outcome_correct, "incorrect", R.string.verif_outcome_incorrect,
            "indetermine", R.string.verif_outcome_indetermine);

    public static String verdict(Context c, String verdict) { return label(c, VERDICTS, verdict); }

    public static String workflow(Context c, String workflow) { return label(c, WORKFLOWS, workflow); }

    public static String status(Context c, String status) { return label(c, STATUSES, status); }

    public static String verificationStatus(Context c, String status) { return label(c, VERIFICATION_STATUSES, status); }

    public static String outcome(Context c, String outcome) { return label(c, OUTCOMES, outcome); }

    @ColorRes
    public static int verdictColor(String verdict) {
        if (verdict == null) return R.color.gray_text;
        switch (verdict) {
            case "fiable":
            case "vrai":
            case "plutot_vrai":
            case "correct":
                return R.color.verdict_good;
            case "plutot_fiable":
            case "mitige":
                return R.color.verdict_fair;
            case "a_verifier":
            case "non_verifiable":
            case "indetermine":
                return R.color.verdict_warn;
            default:
                return R.color.verdict_bad;
        }
    }

    @ColorRes
    public static int scoreColor(Double score) {
        if (score == null) return R.color.gray_text;
        // Mêmes seuils que le web (core/format.ts)
        if (score >= 6.5) return R.color.verdict_good;
        if (score >= 4.5) return R.color.verdict_warn;
        return R.color.verdict_bad;
    }

    /** Markdown réduit à du texte lisible (titres, gras, liens). */
    public static String plainMarkdown(String markdown) {
        if (markdown == null) return "";
        return markdown
                .replaceAll("(?m)^#{1,6}\\s*", "")
                .replaceAll("\\*\\*(.+?)\\*\\*", "$1")
                .replaceAll("(?<!\\*)\\*(?!\\*)(.+?)\\*", "$1")
                .replaceAll("\\[(.+?)]\\((.+?)\\)", "$1 ($2)");
    }
}
