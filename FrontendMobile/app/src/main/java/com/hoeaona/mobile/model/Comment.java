package com.hoeaona.mobile.model;

public class Comment {
    private String id;
    private String created_at;
    private String body;
    private String author_id;
    private String author_name;
    private String author_organization;
    private boolean can_delete;

    public String getId() { return id; }
    public String getCreatedAt() { return created_at; }
    public String getBody() { return body; }
    public String getAuthorName() { return author_name; }
    public String getAuthorOrganization() { return author_organization; }
}
