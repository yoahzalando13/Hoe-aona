package com.hoeaona.mobile.model;

import java.util.List;

public class Health {
    public String status;
    public String mcp_mode;
    public List<String> mcp_tools;
    public List<Provider> providers;

    public static class Provider {
        public String key;
        public String label;
        public String role;
        public boolean configured;
    }
}
