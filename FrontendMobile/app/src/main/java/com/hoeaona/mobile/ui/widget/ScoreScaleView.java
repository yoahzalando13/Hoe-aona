package com.hoeaona.mobile.ui.widget;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.util.AttributeSet;
import android.util.TypedValue;
import android.view.View;
import androidx.annotation.Nullable;
import androidx.core.content.ContextCompat;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.util.Format;

/**
 * Score sur 10 lu comme une règle graduée : rail, graduations, remplissage et curseur triangulaire.
 * Même dessin que le composant « score » du web.
 */
public class ScoreScaleView extends View {
    private final Paint rail = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint tick = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint label = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path marker = new Path();
    private Double score;
    private boolean showLabels = true;

    public ScoreScaleView(Context context, @Nullable AttributeSet attrs) {
        super(context, attrs);
        rail.setColor(ContextCompat.getColor(context, R.color.soft));
        tick.setColor(ContextCompat.getColor(context, R.color.gray_text));
        tick.setStrokeWidth(dp(1));
        label.setColor(ContextCompat.getColor(context, R.color.gray_text));
        label.setTextSize(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, 10, getResources().getDisplayMetrics()));
    }

    private float dp(float v) {
        return v * getResources().getDisplayMetrics().density;
    }

    public void setScore(Double score) {
        this.score = score;
        fill.setColor(ContextCompat.getColor(getContext(), Format.scoreColor(score)));
        invalidate();
    }

    /** Sans chiffres 0, 5, 10 sous la règle (lignes de critères). */
    public void setShowLabels(boolean show) {
        showLabels = show;
        requestLayout();
    }

    @Override
    protected void onMeasure(int widthSpec, int heightSpec) {
        int h = (int) dp(showLabels ? 30 : 16);
        setMeasuredDimension(MeasureSpec.getSize(widthSpec), resolveSize(h, heightSpec));
    }

    @Override
    protected void onDraw(Canvas canvas) {
        float left = dp(4), right = getWidth() - dp(4), w = right - left;
        float railTop = dp(8), railBottom = dp(12);
        canvas.drawRect(left, railTop, right, railBottom, rail);
        float ratio = score == null ? 0f : (float) Math.max(0, Math.min(10, score)) / 10f;
        if (score != null) canvas.drawRect(left, railTop, left + w * ratio, railBottom, fill);
        for (int i = 0; i <= 10; i++) {
            float x = left + w * i / 10f;
            canvas.drawLine(x, i % 5 == 0 ? dp(4) : dp(6.5f), x, railBottom, tick);
        }
        if (score != null) {
            float x = left + w * ratio;
            marker.reset();
            marker.moveTo(x - dp(4.5f), 0);
            marker.lineTo(x + dp(4.5f), 0);
            marker.lineTo(x, dp(6.5f));
            marker.close();
            canvas.drawPath(marker, fill);
        }
        if (showLabels) {
            float y = railBottom + dp(14);
            label.setTextAlign(Paint.Align.LEFT);
            canvas.drawText("0", left - dp(2), y, label);
            label.setTextAlign(Paint.Align.CENTER);
            canvas.drawText("5", left + w / 2, y, label);
            label.setTextAlign(Paint.Align.RIGHT);
            canvas.drawText("10", right + dp(2), y, label);
        }
    }
}
