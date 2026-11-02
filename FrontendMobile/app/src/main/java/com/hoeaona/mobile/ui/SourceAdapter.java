package com.hoeaona.mobile.ui;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.model.OfficialSource;
import java.util.List;

public class SourceAdapter extends RecyclerView.Adapter<SourceAdapter.ViewHolder> {
    private List<OfficialSource> sources;

    public SourceAdapter(List<OfficialSource> sources) {
        this.sources = sources;
    }

    public void setSources(List<OfficialSource> sources) {
        this.sources = sources;
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_source, parent, false);
        return new ViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
        OfficialSource source = sources.get(position);
        holder.tvName.setText(source.getName() + (source.getAcronym() != null && !source.getAcronym().isEmpty() ? " (" + source.getAcronym() + ")" : ""));
        holder.tvCategory.setText(source.getCategory());
        holder.tvWebsite.setText(source.getWebsite());
    }

    @Override
    public int getItemCount() {
        return sources != null ? sources.size() : 0;
    }

    static class ViewHolder extends RecyclerView.ViewHolder {
        TextView tvName, tvCategory, tvWebsite;
        public ViewHolder(@NonNull View itemView) {
            super(itemView);
            tvName = itemView.findViewById(R.id.tvSourceName);
            tvCategory = itemView.findViewById(R.id.tvSourceCategory);
            tvWebsite = itemView.findViewById(R.id.tvSourceWebsite);
        }
    }
}
