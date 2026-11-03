package com.hoeaona.mobile.ui.widget;

import android.content.Context;
import android.view.Gravity;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.core.content.ContextCompat;
import com.hoeaona.mobile.R;

/**
 * Bandeau de chiffres : filet épais au-dessus, chiffres en serif séparés par des filets fins, sans cartes.
 * Même présentation que `.stat-grid` sur le web.
 */
public final class Ledger {
    private Ledger() {}

    /** cells = {chiffre, libellé} ; perRow cellules par ligne. */
    public static void render(LinearLayout parent, String[][] cells, int perRow) {
        Context c = parent.getContext();
        float d = c.getResources().getDisplayMetrics().density;
        parent.removeAllViews();
        parent.setOrientation(LinearLayout.VERTICAL);
        parent.addView(rule(c, (int) (2 * d), R.color.text_primary));
        for (int start = 0; start < cells.length; start += perRow) {
            LinearLayout row = new LinearLayout(c);
            row.setOrientation(LinearLayout.HORIZONTAL);
            for (int i = start; i < start + perRow; i++) {
                if (i > start) {
                    View sep = new View(c);
                    sep.setBackgroundColor(ContextCompat.getColor(c, R.color.gray_border));
                    row.addView(sep, new LinearLayout.LayoutParams((int) d, LinearLayout.LayoutParams.MATCH_PARENT));
                }
                LinearLayout cell = new LinearLayout(c);
                cell.setOrientation(LinearLayout.VERTICAL);
                cell.setPadding(i > start ? (int) (12 * d) : 0, (int) (10 * d), (int) (8 * d), (int) (10 * d));
                if (i < cells.length) {
                    TextView figure = new TextView(c);
                    figure.setTextAppearance(R.style.TextAppearance_Hoe_Figure);
                    figure.setTextSize(28);
                    figure.setText(cells[i][0]);
                    TextView label = new TextView(c);
                    label.setTextAppearance(R.style.TextAppearance_Hoe_Meta);
                    label.setTextColor(ContextCompat.getColor(c, R.color.ink2));
                    label.setText(cells[i][1]);
                    cell.addView(figure);
                    cell.addView(label);
                }
                row.addView(cell, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1));
            }
            row.setGravity(Gravity.TOP);
            parent.addView(row);
            parent.addView(rule(c, (int) d, R.color.gray_border));
        }
    }

    private static View rule(Context c, int height, int color) {
        View v = new View(c);
        v.setBackgroundColor(ContextCompat.getColor(c, color));
        v.setLayoutParams(new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, height));
        return v;
    }
}
