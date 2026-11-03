package com.hoeaona.mobile.model;

import java.util.List;
import java.util.Map;

public class AnalysisStats {
    public int total;
    public Double average_score;
    public Map<String, Integer> by_verdict;
    public Map<String, Integer> by_workflow;
    public Map<String, Integer> by_status;
    public List<TagCount> tags;

    public static class TagCount {
        public String tag;
        public int count;
    }
}
