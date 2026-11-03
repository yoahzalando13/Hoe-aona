package com.hoeaona.mobile.verify;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.model.Verification;
import com.hoeaona.mobile.util.Format;

import java.util.ArrayList;
import java.util.List;

public class VerificationAdapter extends RecyclerView.Adapter<VerificationAdapter.Holder> {
    public interface Listener {
        void onClick(Verification verification);
    }

    private List<Verification> items = new ArrayList<>();
    private final Listener listener;

    public VerificationAdapter(Listener listener) {
        this.listener = listener;
    }

    public void setItems(List<Verification> items) {
        this.items = items != null ? items : new ArrayList<>();
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public Holder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        return new Holder(LayoutInflater.from(parent.getContext()).inflate(R.layout.item_verification, parent, false));
    }

    @Override
    public void onBindViewHolder(@NonNull Holder h, int position) {
        Verification v = items.get(position);
        android.content.Context c = h.itemView.getContext();
        h.tvClaim.setText(v.claim);
        h.tvPlace.setText(v.place_label);
        String status = "completed".equals(v.status) ? Format.outcome(c, v.outcome) : Format.verificationStatus(c, v.status);
        h.tvStatus.setText(status);
        h.tvStatus.setTextColor(c.getColor("completed".equals(v.status) ? Format.verdictColor(v.outcome)
                : "open".equals(v.status) || "accepted".equals(v.status) ? R.color.primary : R.color.gray_text));
        String who = "requester".equals(v.role)
                ? (v.verifier_name != null ? c.getString(R.string.verif_by, v.verifier_name) : "")
                : c.getString(R.string.verif_asked_by, v.requester_name);
        h.tvMeta.setText(Format.date(v.created_at) + (who.isEmpty() ? "" : " · " + who));
        h.itemView.setOnClickListener(x -> listener.onClick(v));
    }

    @Override
    public int getItemCount() {
        return items.size();
    }

    static class Holder extends RecyclerView.ViewHolder {
        final TextView tvClaim, tvPlace, tvStatus, tvMeta;

        Holder(@NonNull View itemView) {
            super(itemView);
            tvClaim = itemView.findViewById(R.id.tvClaim);
            tvPlace = itemView.findViewById(R.id.tvPlace);
            tvStatus = itemView.findViewById(R.id.tvStatus);
            tvMeta = itemView.findViewById(R.id.tvMeta);
        }
    }
}
