package com.hoeaona.mobile.model;

/** Demande de vérification physique. Ne contient jamais la position d'un utilisateur. */
public class Verification {
    public String id;
    public String created_at;
    public String expires_at;
    public String status;       // open, accepted, completed, cancelled, expired
    public String claim;
    public String details;
    public String place_label;
    public double latitude;     // lieu à vérifier
    public double longitude;
    public int radius_m;
    public String analysis_id;
    public String requester_id;
    public String requester_name;
    public String requester_organization;
    public String verifier_id;
    public String verifier_name;
    public String accepted_at;
    public String outcome;      // correct, incorrect, indetermine
    public String report;
    public String photo_url;
    public String completed_at;
    public String role;         // requester, verifier, recipient
}
