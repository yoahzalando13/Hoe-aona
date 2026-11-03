package com.hoeaona.mobile.ui;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.model.AnalysisOut;
import com.hoeaona.mobile.util.Format;

import java.util.ArrayList;
import java.util.List;

public class AnalysisAdapter extends RecyclerView.Adapter<AnalysisAdapter.AnalysisViewHolder> {
    public interface OnAnalysisListener {
        void onAnalysisClick(AnalysisOut analysis);
    }

    private List<AnalysisOut> analyses = new ArrayList<>();
    private final OnAnalysisListener listener;

    public AnalysisAdapter(OnAnalysisListener listener) {
        this.listener = listener;
    }

    public void setAnalyses(List<AnalysisOut> analyses) {
        this.analyses = analyses != null ? analyses : new ArrayList<>();
        notifyDataSetChanged();
    }

    public void addAnalyses(List<AnalysisOut> more) {
        int start = analyses.size();
        analyses.addAll(more);
        notifyItemRangeInserted(start, more.size());
    }

    @NonNull
    @Override
    public AnalysisViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_analysis, parent, false);
        return new AnalysisViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull AnalysisViewHolder holder, int position) {
        AnalysisOut item = analyses.get(position);
        Context c = holder.itemView.getContext();
        holder.tvTitle.setText(item.title);
        boolean done = "done".equals(item.status);
        holder.tvVerdict.setText(done ? Format.verdict(c, item.verdict) : Format.status(c, item.status));
        holder.tvVerdict.setTextColor(c.getColor(done ? Format.verdictColor(item.verdict) : R.color.gray_text));
        holder.tvScore.setText(Format.scoreSpan(c, item.global_score));
        holder.tvScore.setTextColor(c.getColor(Format.scoreColor(item.global_score)));
        String tags = item.tags == null || item.tags.isEmpty() ? "" : " · #" + String.join(" #", item.tags);
        holder.tvDate.setText(Format.date(item.created_at) + " · " + Format.workflow(c, item.workflow) + tags);
        holder.itemView.setOnClickListener(v -> listener.onAnalysisClick(item));
    }

    @Override
    public int getItemCount() {
        return analyses.size();
    }

    static class AnalysisViewHolder extends RecyclerView.ViewHolder {
        TextView tvTitle, tvVerdict, tvScore, tvDate;

        public AnalysisViewHolder(@NonNull View itemView) {
            super(itemView);
            tvTitle = itemView.findViewById(R.id.tvTitle);
            tvVerdict = itemView.findViewById(R.id.tvVerdict);
            tvScore = itemView.findViewById(R.id.tvScore);
            tvDate = itemView.findViewById(R.id.tvDate);
        }
    }
}
