package com.hoeaona.mobile.model;

import java.util.List;

/** Analyse complète (GET /analyses/{id}) ou élément de liste (mêmes champs, sans résultat). */
public class AnalysisOut {
    public String id;
    public String created_at;
    public String updated_at;
    public String status;
    public int progress;
    public String step;
    public String title;
    public String input_kind;
    public Double global_score;
    public String verdict;
    public AnalysisResult result;
    public String error;
    public String notes;
    public List<String> tags;
    public String workflow;
    public List<AgentEvent> events;
    public String owner_id;
    public String owner_name;
    public boolean editable;

    public boolean isFinished() { return "done".equals(status) || "error".equals(status); }

    public static class AgentEvent {
        public double at;
        public String agent;
        public String message;
        public String status;
        public String detail;
        public String tool;
    }
}
