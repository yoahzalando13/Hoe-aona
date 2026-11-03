package com.hoeaona.mobile.model;

public class User {
    public String id;
    public String created_at;
    public String email;
    public String display_name;
    public String organization;
    public String bio;
    public String role;
    public boolean active;
    // Champs de l'administration (AdminUser)
    public int analyses_count;
    public int posts_count;

    public boolean isAdmin() { return "admin".equals(role); }
}
