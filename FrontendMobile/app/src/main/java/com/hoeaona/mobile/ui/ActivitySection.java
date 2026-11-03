package com.hoeaona.mobile.ui;

import android.content.Context;
import android.graphics.Typeface;
import android.view.Gravity;
import android.view.LayoutInflater;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.TextView;
import com.google.android.material.chip.Chip;
import com.google.android.material.chip.ChipGroup;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.model.PlatformActivity;
import com.hoeaona.mobile.ui.widget.Ledger;

import java.text.NumberFormat;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Statistiques de la plateforme : activité par région (classement filetée) et contenus truqués repérés.
 * Même présentation que la page Statistiques du web ; les données fictives sont signalées comme telles.
 */
public class ActivitySection {
    private static final int SORT_RATE = 0, SORT_VOLUME = 1, SORT_DEEPFAKE = 2;

    private final Context c;
    private final LinearLayout root;
    private final PlatformActivity a;
    private final LayoutInflater inflater;
    private final LinearLayout regionList;
    private final TextView regionHint;
    private int sort = SORT_RATE;

    public ActivitySection(Context context, LinearLayout root, PlatformActivity activity) {
        this.c = context;
        this.root = root;
        this.a = activity;
        this.inflater = LayoutInflater.from(context);
        root.removeAllViews();

        header(R.string.activity_title);
        LinearLayout ledger = new LinearLayout(c);
        root.addView(ledger);
        Ledger.render(ledger, new String[][]{
                {integer(a.totals.analyses), c.getString(R.string.activity_fig_analyses, a.period_days)},
                {decimal(a.totals.rate_per_100k), c.getString(R.string.activity_fig_rate)},
                {integer(a.totals.verifications), c.getString(R.string.activity_fig_field)},
                {integer(a.totals.members), c.getString(R.string.activity_fig_members)},
        }, 2);

        ChipGroup chips = new ChipGroup(c);
        chips.setSingleSelection(true);
        chips.setSelectionRequired(true);
        int[] labels = {R.string.activity_sort_rate, R.string.activity_sort_volume, R.string.activity_sort_deepfake};
        for (int i = 0; i < labels.length; i++) {
            Chip chip = new Chip(c, null, com.google.android.material.R.attr.chipStyle);
            chip.setText(labels[i]);
            chip.setCheckable(true);
            chip.setId(View.generateViewId());
            chip.setTag(i);
            chips.addView(chip);
            if (i == SORT_RATE) chip.setChecked(true);
        }
        chips.setOnCheckedStateChangeListener((group, ids) -> {
            if (ids.isEmpty()) return;
            sort = (int) group.findViewById(ids.get(0)).getTag();
            renderRegions();
        });
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        lp.topMargin = dp(12);
        root.addView(chips, lp);
        regionHint = meta("");
        root.addView(regionHint);
        root.addView(rule(dp(2), R.color.text_primary));
        regionList = new LinearLayout(c);
        regionList.setOrientation(LinearLayout.VERTICAL);
        root.addView(regionList);
        renderRegions();

        renderDeepfakes();
    }

    private int dp(int v) {
        return (int) (v * c.getResources().getDisplayMetrics().density);
    }

    private static String integer(int n) {
        return NumberFormat.getIntegerInstance(Locale.getDefault()).format(n);
    }

    private static String decimal(double v) {
        return String.format(Locale.getDefault(), v == Math.rint(v) ? "%.0f" : "%.1f", v);
    }

    /** Intertitre de rubrique sous un filet, avec la mention « données fictives » si besoin. */
    private void header(int title) {
        LinearLayout.LayoutParams top = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(1));
        top.topMargin = dp(28);
        View line = new View(c);
        line.setBackgroundColor(c.getColor(R.color.text_primary));
        root.addView(line, top);
        TextView label = new TextView(c);
        label.setTextAppearance(R.style.TextAppearance_Hoe_SectionLabel);
        label.setText(title);
        label.setPadding(0, dp(8), 0, dp(4));
        root.addView(label);
        if (a.demo) {
            TextView demo = new TextView(c);
            demo.setText(R.string.activity_demo);
            demo.setTextSize(10);
            demo.setAllCaps(true);
            demo.setLetterSpacing(0.06f);
            demo.setTextColor(c.getColor(R.color.verdict_warn));
            demo.setPadding(0, 0, 0, dp(8));
            root.addView(demo);
        }
    }

    private TextView meta(String text) {
        TextView t = new TextView(c);
        t.setTextAppearance(R.style.TextAppearance_Hoe_Meta);
        t.setText(text);
        t.setPadding(0, dp(4), 0, dp(8));
        return t;
    }

    private View rule(int height, int color) {
        View v = new View(c);
        v.setBackgroundColor(c.getColor(color));
        v.setLayoutParams(new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, height));
        return v;
    }

    private double value(PlatformActivity.Region r) {
        return sort == SORT_VOLUME ? r.analyses : sort == SORT_DEEPFAKE ? r.deepfake_rate : r.rate_per_100k;
    }

    private void renderRegions() {
        regionHint.setText(sort == SORT_VOLUME ? R.string.activity_hint_volume
                : sort == SORT_DEEPFAKE ? R.string.activity_hint_deepfake : R.string.activity_hint_rate);
        List<PlatformActivity.Region> rows = new ArrayList<>(a.regions);
        rows.sort((x, y) -> Double.compare(value(y), value(x)));
        double max = 1;
        for (PlatformActivity.Region r : rows) max = Math.max(max, value(r));
        regionList.removeAllViews();
        for (int i = 0; i < rows.size(); i++) {
            PlatformActivity.Region r = rows.get(i);
            View row = inflater.inflate(R.layout.item_region, regionList, false);
            boolean top = i < 3;
            TextView rank = row.findViewById(R.id.tvRank);
            rank.setText(String.valueOf(i + 1));
            if (top) {
                rank.setTextColor(c.getColor(R.color.brand));
                rank.setTypeface(rank.getTypeface(), Typeface.BOLD);
            }
            ((TextView) row.findViewById(R.id.tvName)).setText(r.name);
            ((TextView) row.findViewById(R.id.tvSub)).setText(c.getString(R.string.activity_region_sub, r.capital,
                    integer(r.analyses), integer(r.verifications)));
            String unit = sort == SORT_DEEPFAKE ? " %" : sort == SORT_RATE ? " /100k" : "";
            ((TextView) row.findViewById(R.id.tvValue)).setText(
                    (sort == SORT_VOLUME ? integer(r.analyses) : decimal(value(r))) + unit);
            TextView trend = row.findViewById(R.id.tvTrend);
            if (sort == SORT_DEEPFAKE) {
                trend.setText(c.getString(R.string.activity_fakes_of, r.deepfakes, r.media_analysed));
            } else if (r.trend_pct != null) {
                trend.setText((r.trend_pct > 0 ? "▲ " : r.trend_pct < 0 ? "▼ " : "= ") + decimal(r.trend_pct) + " %");
                trend.setTextColor(c.getColor(r.trend_pct > 0 ? R.color.verdict_good
                        : r.trend_pct < 0 ? R.color.verdict_bad : R.color.gray_text));
            }
            float share = (float) (value(r) / max);
            View fill = row.findViewById(R.id.fill);
            fill.setLayoutParams(new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, Math.max(share, 0.01f)));
            fill.setBackgroundColor(c.getColor(sort == SORT_DEEPFAKE ? R.color.verdict_warn
                    : top ? R.color.brand : R.color.text_primary));
            row.findViewById(R.id.rest).setLayoutParams(
                    new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, 1f - share));
            regionList.addView(row);
        }
    }

    /** Chiffre de une, répartition par type, puis colonnes mensuelles (le dernier mois en cramoisi). */
    private void renderDeepfakes() {
        header(R.string.activity_deepfake_title);
        root.addView(rule(dp(2), R.color.text_primary));
        TextView rate = new TextView(c);
        rate.setTextAppearance(R.style.TextAppearance_Hoe_Figure);
        rate.setTextSize(64);
        rate.setTextColor(c.getColor(R.color.brand));
        rate.setText(decimal(a.totals.deepfake_rate) + " %");
        rate.setPadding(0, dp(8), 0, 0);
        root.addView(rate);
        TextView sentence = new TextView(c);
        sentence.setTextAppearance(R.style.TextAppearance_Hoe_Body);
        sentence.setTextColor(c.getColor(R.color.ink2));
        sentence.setText(c.getString(R.string.activity_deepfake_sentence, a.period_days,
                integer(a.totals.deepfakes), integer(a.totals.media_analysed)));
        root.addView(sentence);

        root.addView(spacer(12));
        root.addView(rule(dp(1), R.color.gray_border));
        for (PlatformActivity.Kind k : a.deepfake_by_kind) {
            View row = inflater.inflate(R.layout.item_compare, root, false);
            TextView name = row.findViewById(R.id.tvCountry);
            name.setText(kindLabel(k.kind, k.label));
            name.setMaxLines(2);
            name.getLayoutParams().width = dp(150);
            float share = (float) (k.share / 100);
            View fill = row.findViewById(R.id.fill);
            fill.setLayoutParams(new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, share));
            fill.setBackgroundColor(c.getColor(R.color.verdict_warn));
            row.findViewById(R.id.rest).setLayoutParams(new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, 1f - share));
            ((TextView) row.findViewById(R.id.tvValue)).setText(decimal(k.share) + " %");
            root.addView(row);
            root.addView(rule(dp(1), R.color.gray_border));
        }

        TextView caption = new TextView(c);
        caption.setTextAppearance(R.style.TextAppearance_Hoe_SectionLabel);
        caption.setText(R.string.activity_monthly);
        caption.setPadding(0, dp(20), 0, dp(8));
        root.addView(caption);
        double max = 1;
        for (PlatformActivity.Month m : a.deepfake_monthly) max = Math.max(max, m.rate);
        LinearLayout cols = new LinearLayout(c);
        cols.setOrientation(LinearLayout.HORIZONTAL);
        cols.setGravity(Gravity.BOTTOM);
        for (int i = 0; i < a.deepfake_monthly.size(); i++) {
            PlatformActivity.Month m = a.deepfake_monthly.get(i);
            boolean last = i == a.deepfake_monthly.size() - 1;
            LinearLayout col = new LinearLayout(c);
            col.setOrientation(LinearLayout.VERTICAL);
            col.setGravity(Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL);
            TextView v = new TextView(c);
            v.setTextSize(9);
            v.setTypeface(Typeface.SERIF, last ? Typeface.BOLD : Typeface.NORMAL);
            v.setTextColor(c.getColor(last ? R.color.brand : R.color.ink2));
            v.setText(decimal(m.rate));
            col.addView(v);
            View bar = new View(c);
            bar.setBackgroundColor(c.getColor(last ? R.color.brand : R.color.line_strong));
            LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT,
                    (int) (dp(110) * m.rate / max));
            blp.topMargin = dp(2);
            col.addView(bar, blp);
            LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1);
            clp.setMargins(dp(2), 0, dp(2), 0);
            cols.addView(col, clp);
        }
        root.addView(cols);
        root.addView(rule(dp(1), R.color.text_primary));
        // Mois : le premier et le dernier, pour situer la période sans encombrer l'axe.
        LinearLayout axis = new LinearLayout(c);
        axis.setOrientation(LinearLayout.HORIZONTAL);
        TextView first = meta(a.deepfake_monthly.get(0).month);
        TextView lastLabel = meta(a.deepfake_monthly.get(a.deepfake_monthly.size() - 1).month);
        lastLabel.setGravity(Gravity.END);
        axis.addView(first, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1));
        axis.addView(lastLabel, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1));
        root.addView(axis);
    }

    private View spacer(int height) {
        View v = new View(c);
        v.setLayoutParams(new LinearLayout.LayoutParams(1, dp(height)));
        return v;
    }

    private String kindLabel(String kind, String fallback) {
        switch (kind) {
            case "image": return c.getString(R.string.activity_kind_image);
            case "voix": return c.getString(R.string.activity_kind_voice);
            case "video": return c.getString(R.string.activity_kind_video);
            case "texte": return c.getString(R.string.activity_kind_text);
            default: return fallback;
        }
    }
}
