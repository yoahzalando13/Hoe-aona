package com.hoeaona.mobile.ui;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import androidx.appcompat.app.AppCompatActivity;
import androidx.fragment.app.Fragment;
import com.google.android.material.appbar.MaterialToolbar;
import com.hoeaona.mobile.R;

/** Écrans secondaires du menu « Plus » : barre de titre et un fragment. */
public class HostActivity extends AppCompatActivity {
    public static final String EXTRA_SCREEN = "screen";
    public static final String SOURCES = "sources", STATS = "stats", SETTINGS = "settings", ADMIN = "admin",
            NOTIFICATIONS = "notifications";

    public static Intent intent(Context context, String screen) {
        return new Intent(context, HostActivity.class).putExtra(EXTRA_SCREEN, screen);
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_host);
        MaterialToolbar toolbar = findViewById(R.id.toolbar);
        toolbar.setNavigationOnClickListener(v -> finish());

        String screen = getIntent().getStringExtra(EXTRA_SCREEN);
        Fragment fragment;
        int title;
        if (STATS.equals(screen)) {
            fragment = new StatsFragment();
            title = R.string.more_stats;
        } else if (SETTINGS.equals(screen)) {
            fragment = new SettingsFragment();
            title = R.string.more_settings;
        } else if (ADMIN.equals(screen)) {
            fragment = new AdminFragment();
            title = R.string.more_admin;
        } else if (NOTIFICATIONS.equals(screen)) {
            fragment = new NotificationsFragment();
            title = R.string.more_notifications;
        } else {
            fragment = new SourcesFragment();
            title = R.string.more_sources;
        }
        toolbar.setTitle(title);
        if (savedInstanceState == null) {
            getSupportFragmentManager().beginTransaction().replace(R.id.fragmentContainer, fragment).commit();
        }
    }
}
