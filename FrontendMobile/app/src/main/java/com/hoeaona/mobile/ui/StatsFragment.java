package com.hoeaona.mobile.ui;

import android.graphics.Typeface;
import android.os.Bundle;
import android.text.SpannableString;
import android.text.Spanned;
import android.text.style.ForegroundColorSpan;
import android.text.style.RelativeSizeSpan;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AlertDialog;
import androidx.fragment.app.Fragment;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.StatSeries;
import com.hoeaona.mobile.util.Format;
import com.hoeaona.mobile.util.Links;

import java.util.ArrayList;
import java.util.List;

/** Chiffres clés de Madagascar (Banque mondiale, estimation FMI) et comparaison avec les pays voisins. */
public class StatsFragment extends Fragment {
    private LinearLayout layoutStats;
    private ProgressBar progress;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_stats, container, false);
        layoutStats = view.findViewById(R.id.layoutStats);
        progress = view.findViewById(R.id.progress);
        ApiClient.getApiService().statsMadagascar().enqueue(new ApiCallback<List<StatSeries>>(getViewLifecycleOwner()) {
            @Override
            public void onSuccess(List<StatSeries> body) {
                for (StatSeries s : body) if (s.ok) layoutStats.addView(row(inflater, s));
            }

            @Override
            public void onFinally() {
                progress.setVisibility(View.GONE);
            }
        });
        return view;
    }

    private View row(LayoutInflater inflater, StatSeries s) {
        View row = inflater.inflate(R.layout.item_stat, layoutStats, false);
        ((TextView) row.findViewById(R.id.tvName)).setText(s.indicator_name);
        ((TextView) row.findViewById(R.id.tvValue)).setText(figure(s.latest_value, s.unit));
        String year = s.latest_year == null ? "–" : String.valueOf(s.latest_year);
        String meta = s.imf != null && s.imf.ok && s.imf.latest_year != null
                ? getString(R.string.stats_year_imf, year, String.valueOf(s.imf.latest_year), Format.number(s.imf.latest_value))
                : year;
        TextView tvMeta = row.findViewById(R.id.tvMeta);
        tvMeta.setText(meta);
        // Une valeur officielle de plus de deux ans est signalée, comme sur le web.
        boolean old = s.latest_year != null && java.time.Year.now().getValue() - s.latest_year > 2;
        tvMeta.setTextColor(requireContext().getColor(old ? R.color.verdict_warn : R.color.gray_text));
        row.setOnClickListener(v -> compare(s));
        return row;
    }

    /** Chiffre en serif suivi de l'unité, plus petite et plus pâle. */
    private CharSequence figure(Double value, String unit) {
        String number = Format.number(value);
        String u = unit == null ? "" : shortUnit(unit);
        SpannableString out = new SpannableString(u.isEmpty() ? number : number + " " + u);
        if (!u.isEmpty()) {
            out.setSpan(new RelativeSizeSpan(0.5f), number.length(), out.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            out.setSpan(new ForegroundColorSpan(requireContext().getColor(R.color.gray_text)), number.length(), out.length(),
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        }
        return out;
    }

    /** « % de la population » → « % », « US$ courants » → « US$ » : l'unité complète reste dans le libellé. */
    private static String shortUnit(String unit) {
        String u = unit.trim();
        int cut = u.indexOf(' ');
        return cut > 0 && u.length() > 8 ? u.substring(0, cut) : u;
    }

    private void compare(StatSeries s) {
        ApiClient.getApiService().statsCompare(s.indicator_code).enqueue(new ApiCallback<List<StatSeries>>(getViewLifecycleOwner()) {
            @Override
            public void onSuccess(List<StatSeries> body) {
                List<StatSeries> rows = new ArrayList<>();
                for (StatSeries c : body) if (c.ok && c.latest_value != null) rows.add(c);
                rows.sort((a, b) -> Double.compare(b.latest_value, a.latest_value));
                double max = 0;
                for (StatSeries c : rows) max = Math.max(max, Math.abs(c.latest_value));

                LayoutInflater inflater = LayoutInflater.from(requireContext());
                LinearLayout list = new LinearLayout(requireContext());
                list.setOrientation(LinearLayout.VERTICAL);
                int pad = (int) (20 * getResources().getDisplayMetrics().density);
                list.setPadding(pad, pad / 2, pad, 0);
                TextView unit = new TextView(requireContext());
                unit.setTextAppearance(R.style.TextAppearance_Hoe_Meta);
                unit.setText(s.unit);
                list.addView(unit);
                for (StatSeries c : rows) {
                    View row = inflater.inflate(R.layout.item_compare, list, false);
                    boolean mg = "MDG".equals(c.country_code);
                    TextView name = row.findViewById(R.id.tvCountry);
                    name.setText(c.country);
                    if (mg) name.setTypeface(null, Typeface.BOLD);
                    float share = max > 0 ? (float) (Math.abs(c.latest_value) / max) : 0f;
                    View fill = row.findViewById(R.id.fill);
                    fill.setLayoutParams(new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, Math.max(share, 0.01f)));
                    row.findViewById(R.id.rest).setLayoutParams(
                            new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, 1f - share));
                    int color = requireContext().getColor(mg ? R.color.brand : c.latest_value < 0 ? R.color.verdict_warn : R.color.line_strong);
                    fill.setBackgroundColor(color);
                    TextView value = row.findViewById(R.id.tvValue);
                    value.setText(Format.number(c.latest_value) + (c.latest_year != null ? "  " + c.latest_year : ""));
                    if (mg) value.setTextColor(requireContext().getColor(R.color.brand));
                    list.addView(row);
                }
                ScrollView scroll = new ScrollView(requireContext());
                scroll.addView(list);
                new AlertDialog.Builder(requireContext())
                        .setTitle(s.indicator_name)
                        .setView(scroll)
                        .setPositiveButton(R.string.close, null)
                        .setNeutralButton(R.string.stats_open_source, (d, w) -> Links.open(requireContext(), s.source_url))
                        .show();
            }
        });
    }
}
