package com.hoeaona.mobile.model;

public class Post {
    public String id;
    public String created_at;
    public String updated_at;
    public String body;
    public String author_id;
    public String author_name;
    public String author_organization;
    public String author_role;
    public String image_url;
    public PostAnalysis analysis;
    public int likes;
    public boolean liked;
    public int comments_count;
    public boolean hidden;
    public boolean can_edit;
    public boolean can_moderate;

    public static class PostAnalysis {
        public String id;
        public String title;
        public Double global_score;
        public String verdict;
        public String input_kind;
    }
}
