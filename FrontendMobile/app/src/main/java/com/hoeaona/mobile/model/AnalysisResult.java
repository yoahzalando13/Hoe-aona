package com.hoeaona.mobile.model;

import java.util.List;

public class AnalysisResult {
    public double global_score;
    public String verdict;
    public String verdict_label;
    public String summary;
    public String topic;
    public List<Criterion> criteria;
    public List<Claim> claims;
    public List<InputSummary> inputs;
    public List<ExcludedSource> excluded_sources;
    public Article article;
    public List<String> warnings;
    public List<String> tools_used;

    public static class Criterion {
        public String key;
        public String label;
        public double score;
        public String summary;
        public List<String> details;
    }

    public static class InputSummary {
        public String kind;
        public String name;
        public double ai_probability;
        public Double reliability;
        public String url;
        public String note;
    }

    public static class ExcludedSource {
        public String url;
        public String title;
        public String reason;
        public double ai_probability;
    }

    public static class Claim {
        public String id;
        public String text;
        public double truth_score;
        public String verdict;
        public String verdict_label;
        public String conclusion;
        public List<String> arguments_for;
        public List<String> arguments_against;
        public List<Evidence> evidence;
        public List<Statistic> statistics;
        public List<OfficialContact> contacts;
        public List<ReasoningTest> reasoning;
        public boolean universal;
        public Double score_before_reasoning;
        public double reasoning_adjustment;
    }

    public static class Evidence {
        public String id;
        public String url;
        public String title;
        public String publisher;
        public String domain;
        public boolean official;
        public String published_at;
        public String excerpt;
        public double reliability;
        public String stance;
        public String justification;
    }

    public static class Statistic {
        public String id;
        public String indicator_name;
        public String country;
        public Integer latest_year;
        public Double latest_value;
        public String unit;
        public String claimed_value;
        public String source_name;
        public String source_url;
        public String stance;
        public String comment;
    }

    public static class ReasoningTest {
        public String kind;
        public String label;
        public String outcome;
        public String summary;
        public String effect;
    }

    public static class Article {
        public String title;
        public String lead;
        public String body_markdown;
        public List<String> tags;
        public List<String> key_points;
        public String social_post;
        public List<ArticleSource> sources;
        public String generated_by;
        public boolean edited;
    }

    public static class ArticleSource {
        public int n;
        public String title;
        public String publisher;
        public String url;
    }
}
