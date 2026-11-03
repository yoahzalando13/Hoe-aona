package com.hoeaona.mobile.ui;

import android.view.View;
import android.view.ViewGroup;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import com.hoeaona.mobile.model.OfficialContact;
import com.hoeaona.mobile.util.ContactViews;

import java.util.ArrayList;
import java.util.List;

public class SourceAdapter extends RecyclerView.Adapter<SourceAdapter.SourceViewHolder> {
    private List<OfficialContact> sources = new ArrayList<>();

    public void setSources(List<OfficialContact> sources) {
        this.sources = sources != null ? sources : new ArrayList<>();
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public SourceViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        return new SourceViewHolder(ContactViews.inflate(parent));
    }

    @Override
    public void onBindViewHolder(@NonNull SourceViewHolder holder, int position) {
        ContactViews.bind(holder.itemView, sources.get(position));
    }

    @Override
    public int getItemCount() {
        return sources.size();
    }

    static class SourceViewHolder extends RecyclerView.ViewHolder {
        SourceViewHolder(@NonNull View itemView) {
            super(itemView);
        }
    }
}
