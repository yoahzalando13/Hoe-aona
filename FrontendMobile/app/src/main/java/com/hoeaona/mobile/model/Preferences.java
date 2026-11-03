package com.hoeaona.mobile.model;

public class Preferences {
    public int weight_source = 40;
    public int weight_veracity = 40;
    public int weight_ai = 20;
    public boolean deep_ai_detection = true;
    public double ai_exclusion_threshold = 0.7;
    public double min_source_reliability = 0.35;
    public String default_country = "MDG";
    public String report_language = "fr";
    public String ui_language;
    public int history_retention_days = 90;
}
