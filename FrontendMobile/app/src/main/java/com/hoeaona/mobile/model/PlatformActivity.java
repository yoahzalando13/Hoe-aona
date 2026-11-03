package com.hoeaona.mobile.model;

import java.util.List;

/** Activité par région et contenus truqués (GET /stats/activity). Données fictives tant que `demo` est vrai. */
public class PlatformActivity {
    public boolean demo;
    public int period_days;
    public Totals totals;
    public List<Region> regions;
    public List<Kind> deepfake_by_kind;
    public List<Month> deepfake_monthly;

    public static class Totals {
        public int analyses;
        public int verifications;
        public int members;
        public double rate_per_100k;
        public int media_analysed;
        public int deepfakes;
        public double deepfake_rate;
    }

    public static class Region {
        public String code;
        public String name;
        public String capital;
        public int analyses;
        public int verifications;
        public double rate_per_100k;
        public Double trend_pct;
        public int media_analysed;
        public int deepfakes;
        public double deepfake_rate;
    }

    public static class Kind {
        public String kind;
        public String label;
        public double share;
    }

    public static class Month {
        public String month;
        public double rate;
    }
}
