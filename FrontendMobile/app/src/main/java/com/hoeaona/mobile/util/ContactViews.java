package com.hoeaona.mobile.util;

import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.model.OfficialContact;

/** Fiche d'institution avec appel, e-mail et site : annuaire et « Qui contacter pour confirmer ». */
public final class ContactViews {
    private ContactViews() {}

    public static View inflate(ViewGroup parent) {
        return LayoutInflater.from(parent.getContext()).inflate(R.layout.item_source, parent, false);
    }

    public static void bind(View view, OfficialContact s) {
        Context c = view.getContext();
        String acronym = s.acronym != null && !s.acronym.isEmpty() ? " (" + s.acronym + ")" : "";
        ((TextView) view.findViewById(R.id.tvName)).setText(s.name + acronym);
        text(view.findViewById(R.id.tvCategory), s.category);
        text(view.findViewById(R.id.tvNotes), s.reason != null && !s.reason.isEmpty() ? s.reason : s.notes);
        text(view.findViewById(R.id.tvAddress), s.address);
        String phone = s.phone == null ? "" : s.phone.split("[/;,]")[0].trim();
        action(view.findViewById(R.id.btnCall), phone, () ->
                c.startActivity(new Intent(Intent.ACTION_DIAL, Uri.parse("tel:" + phone.replaceAll("[^+\\d]", "")))));
        action(view.findViewById(R.id.btnEmail), s.email, () ->
                c.startActivity(new Intent(Intent.ACTION_SENDTO, Uri.parse("mailto:" + s.email.split("[;,\\s]")[0]))));
        action(view.findViewById(R.id.btnWebsite), s.website, () -> Links.open(c, s.website));
    }

    private static void text(TextView view, String value) {
        view.setText(value);
        view.setVisibility(value == null || value.isEmpty() ? View.GONE : View.VISIBLE);
    }

    private static void action(View button, String value, Runnable run) {
        button.setVisibility(value == null || value.isEmpty() ? View.GONE : View.VISIBLE);
        button.setOnClickListener(v -> {
            try {
                run.run();
            } catch (Exception ignored) {
                // aucune application pour cette action
            }
        });
    }
}
