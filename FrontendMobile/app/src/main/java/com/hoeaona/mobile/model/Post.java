package com.hoeaona.mobile.model;

public class Post {
    private String id;
    private String created_at;
    private String updated_at;
    private String body;
    private String author_id;
    private String author_name;
    private String author_organization;
    private String author_role;
    private String image_url;
    private PostAnalysis analysis;
    private int likes;
    private boolean liked;
    private int comments_count;
    private boolean hidden;
    private boolean can_edit;
    private boolean can_moderate;

    public static class PostAnalysis {
        private String id;
        private String title;
        private Double global_score;
        private String verdict;
        private String input_kind;
        public String getId() { return id; }
        public String getTitle() { return title; }
        public Double getGlobalScore() { return global_score; }
        public String getVerdict() { return verdict; }
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getCreatedAt() { return created_at; }
    public String getBody() { return body; }
    public void setBody(String body) { this.body = body; }
    public String getAuthorName() { return author_name; }
    public void setAuthorName(String author_name) { this.author_name = author_name; }
    public String getAuthorOrganization() { return author_organization; }
    public PostAnalysis getAnalysis() { return analysis; }
    public int getLikes() { return likes; }
    public void setLikes(int likes) { this.likes = likes; }
    public boolean isLiked() { return liked; }
    public void setLiked(boolean liked) { this.liked = liked; }
    public int getCommentsCount() { return comments_count; }
}
