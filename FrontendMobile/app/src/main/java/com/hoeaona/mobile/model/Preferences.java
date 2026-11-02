package com.hoeaona.mobile.model;

public class Preferences {
    private double weight_source;
    private double weight_veracity;
    private double weight_ai;
    private boolean deep_ai_detection;
    private double ai_exclusion_threshold;
    private double min_source_reliability;
    private String default_country;
    private String report_language;
    private int history_retention_days;

    public double getWeightSource() { return weight_source; }
    public void setWeightSource(double w) { this.weight_source = w; }
    public double getWeightVeracity() { return weight_veracity; }
    public void setWeightVeracity(double w) { this.weight_veracity = w; }
    public double getWeightAi() { return weight_ai; }
    public void setWeightAi(double w) { this.weight_ai = w; }
    public boolean isDeepAiDetection() { return deep_ai_detection; }
    public void setDeepAiDetection(boolean d) { this.deep_ai_detection = d; }
    public double getAiExclusionThreshold() { return ai_exclusion_threshold; }
    public void setAiExclusionThreshold(double a) { this.ai_exclusion_threshold = a; }
    public double getMinSourceReliability() { return min_source_reliability; }
    public void setMinSourceReliability(double m) { this.min_source_reliability = m; }
    public String getDefaultCountry() { return default_country; }
    public void setDefaultCountry(String c) { this.default_country = c; }
    public String getReportLanguage() { return report_language; }
    public void setReportLanguage(String l) { this.report_language = l; }
    public int getHistoryRetentionDays() { return history_retention_days; }
    public void setHistoryRetentionDays(int h) { this.history_retention_days = h; }
}
