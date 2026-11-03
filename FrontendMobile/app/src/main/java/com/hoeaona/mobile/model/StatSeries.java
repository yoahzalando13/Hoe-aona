package com.hoeaona.mobile.model;

/** Indicateur FMI ou Banque mondiale (routes /stats). */
public class StatSeries {
    public boolean ok;
    public String provider;
    public String indicator_code;
    public String indicator_name;
    public String unit;
    public String country;
    public String country_code;
    public Integer latest_year;
    public Double latest_value;
    public String source_name;
    public String source_url;
    public String error;
    public StatSeries imf;
}
