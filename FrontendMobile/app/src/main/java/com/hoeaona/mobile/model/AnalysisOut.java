package com.hoeaona.mobile.model;

import com.google.gson.JsonObject;
import java.util.List;

public class AnalysisOut {
    private String id;
    private String created_at;
    private String updated_at;
    private String status;
    private double progress;
    private String step;
    private String title;
    private String input_kind;
    private Double global_score;
    private String verdict;
    private JsonObject result;
    private String error;
    private String notes;
    private List<String> tags;
    private String workflow;
    private String owner_id;
    private String owner_name;
    private boolean editable;

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getCreatedAt() { return created_at; }
    public void setCreatedAt(String c) { this.created_at = c; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getInputKind() { return input_kind; }
    public void setInputKind(String i) { this.input_kind = i; }
    public Double getGlobalScore() { return global_score; }
    public void setGlobalScore(Double g) { this.global_score = g; }
    public String getVerdict() { return verdict; }
    public void setVerdict(String v) { this.verdict = v; }
    public JsonObject getResult() { return result; }
    public void setResult(JsonObject r) { this.result = r; }
    public String getNotes() { return notes; }
    public void setNotes(String notes) { this.notes = notes; }
    public List<String> getTags() { return tags; }
    public void setTags(List<String> tags) { this.tags = tags; }
    public String getWorkflow() { return workflow; }
    public void setWorkflow(String workflow) { this.workflow = workflow; }
}
