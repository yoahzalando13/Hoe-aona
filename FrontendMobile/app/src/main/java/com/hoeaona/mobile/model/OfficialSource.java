package com.hoeaona.mobile.model;

import java.util.List;

public class OfficialSource {
    private String id;
    private String name;
    private String acronym;
    private String category;
    private String website;
    private String email;
    private String phone;
    private String address;
    private String notes;
    private List<String> topics;
    private String verified_at;
    private boolean active;

    public String getId() { return id; }
    public String getName() { return name; }
    public String getAcronym() { return acronym; }
    public String getCategory() { return category; }
    public String getWebsite() { return website; }
    public String getEmail() { return email; }
    public String getPhone() { return phone; }
    public String getAddress() { return address; }
    public String getNotes() { return notes; }
    public List<String> getTopics() { return topics; }
    public boolean isActive() { return active; }
}
