package com.hoeaona.mobile.ui;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.model.AnalysisOut;
import java.util.List;

public class AnalysisAdapter extends RecyclerView.Adapter<AnalysisAdapter.ViewHolder> {
    private List<AnalysisOut> analyses;
    private final OnItemClickListener listener;

    public interface OnItemClickListener {
        void onItemClick(AnalysisOut analysis);
    }

    public AnalysisAdapter(List<AnalysisOut> analyses, OnItemClickListener listener) {
        this.analyses = analyses;
        this.listener = listener;
    }

    public void setAnalyses(List<AnalysisOut> analyses) {
        this.analyses = analyses;
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_analysis, parent, false);
        return new ViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
        AnalysisOut item = analyses.get(position);
        holder.tvTitle.setText(item.getTitle() != null ? item.getTitle() : "Analyse sans titre");
        holder.tvVerdict.setText("Verdict : " + (item.getVerdict() != null ? item.getVerdict() : item.getStatus()));
        holder.tvScore.setText(item.getGlobalScore() != null ? String.format("%.0f%%", item.getGlobalScore() * 100) : "--");
        holder.tvDate.setText(item.getCreatedAt() != null ? item.getCreatedAt().substring(0, 10) : "");
        holder.itemView.setOnClickListener(v -> {
            if (listener != null) listener.onItemClick(item);
        });
    }

    @Override
    public int getItemCount() {
        return analyses != null ? analyses.size() : 0;
    }

    static class ViewHolder extends RecyclerView.ViewHolder {
        TextView tvTitle, tvVerdict, tvScore, tvDate;
        public ViewHolder(@NonNull View itemView) {
            super(itemView);
            tvTitle = itemView.findViewById(R.id.tvAnalysisTitle);
            tvVerdict = itemView.findViewById(R.id.tvAnalysisVerdict);
            tvScore = itemView.findViewById(R.id.tvAnalysisScore);
            tvDate = itemView.findViewById(R.id.tvAnalysisDate);
        }
    }
}
