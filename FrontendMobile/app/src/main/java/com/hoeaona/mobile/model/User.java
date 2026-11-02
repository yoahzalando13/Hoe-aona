package com.hoeaona.mobile.model;

public class User {
    private String id;
    private String created_at;
    private String email;
    private String display_name;
    private String organization;
    private String bio;
    private String role;
    private boolean active;

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getCreatedAt() { return created_at; }
    public void setCreatedAt(String created_at) { this.created_at = created_at; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getDisplayName() { return display_name; }
    public void setDisplayName(String display_name) { this.display_name = display_name; }
    public String getOrganization() { return organization; }
    public void setOrganization(String organization) { this.organization = organization; }
    public String getBio() { return bio; }
    public void setBio(String bio) { this.bio = bio; }
    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }
    public boolean isActive() { return active; }
    public void setActive(boolean active) { this.active = active; }
}
