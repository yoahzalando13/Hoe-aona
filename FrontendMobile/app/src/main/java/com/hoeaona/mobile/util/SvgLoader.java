package com.hoeaona.mobile.util;

import android.graphics.drawable.PictureDrawable;
import android.widget.ImageView;
import com.caverock.androidsvg.SVG;
import com.caverock.androidsvg.SVGParseException;

public class SvgLoader {
    public static void loadSvg(ImageView imageView, String assetName) {
        try {
            SVG svg = SVG.getFromAsset(imageView.getContext().getAssets(), assetName);
            imageView.setImageDrawable(new PictureDrawable(svg.renderToPicture()));
        } catch (SVGParseException | java.io.IOException e) {
            e.printStackTrace();
        }
    }
}
