package com.hoeaona.mobile;

import android.Manifest;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;
import androidx.fragment.app.Fragment;
import com.google.android.material.bottomnavigation.BottomNavigationView;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.User;
import com.hoeaona.mobile.ui.*;
import com.hoeaona.mobile.util.Session;
import com.hoeaona.mobile.verify.LocationReporter;
import com.hoeaona.mobile.verify.VerificationNotifier;
import com.hoeaona.mobile.verify.VerifyFragment;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends AppCompatActivity {
    public static final String EXTRA_TAB = "tab";
    private static final long POLL_MS = 30_000;
    private static final long LOCATION_MS = 5 * 60_000;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private long lastLocationReport;
    private boolean reader;

    /** Application ouverte : notifications toutes les 30 s, position toutes les 5 min (si partagée). */
    private final Runnable poller = new Runnable() {
        @Override
        public void run() {
            if (System.currentTimeMillis() - lastLocationReport > LOCATION_MS) {
                lastLocationReport = System.currentTimeMillis();
                LocationReporter.reportAsync(MainActivity.this);
            }
            executor.execute(() -> VerificationNotifier.poll(getApplicationContext()));
            handler.postDelayed(this, POLL_MS);
        }
    };

    private final ActivityResultLauncher<String> notificationPermission = registerForActivityResult(
            new ActivityResultContracts.RequestPermission(), granted -> {});

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        BottomNavigationView bottomNavigationView = findViewById(R.id.bottomNavigationView);
        reader = Session.isReader(this);
        if (reader) {
            // Lecteur : actualités et menu « Plus » seulement, aucune fonction de rédaction.
            bottomNavigationView.getMenu().clear();
            bottomNavigationView.inflateMenu(R.menu.bottom_nav_reader);
        }

        bottomNavigationView.setOnItemSelectedListener(item -> {
            Fragment selectedFragment = null;
            int itemId = item.getItemId();
            if (itemId == R.id.nav_feed) {
                selectedFragment = new FeedFragment();
            } else if (itemId == R.id.nav_analyze) {
                selectedFragment = new AnalyzeFragment();
            } else if (itemId == R.id.nav_verify) {
                selectedFragment = new VerifyFragment();
            } else if (itemId == R.id.nav_workspace) {
                selectedFragment = new WorkspaceFragment();
            } else if (itemId == R.id.nav_more) {
                selectedFragment = new MoreFragment();
            }

            if (selectedFragment != null) {
                loadFragment(selectedFragment);
                return true;
            }
            return false;
        });

        if (savedInstanceState == null) {
            bottomNavigationView.setSelectedItemId(getIntent().getIntExtra(EXTRA_TAB, R.id.nav_feed));
        }

        // Le rôle a pu changer (administrateur) : on recharge l'interface si besoin.
        ApiClient.getApiService().getMe().enqueue(new ApiCallback<User>(this) {
            @Override
            public void onSuccess(User me) {
                boolean nowReader = "reader".equals(me.role);
                Session.save(MainActivity.this, me);
                if (nowReader != reader) recreate();
            }

            @Override
            public void onError(int code, String message) {}
        });

        if (!reader && Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
            notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS);
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        lastLocationReport = 0;
        if (!reader) handler.post(poller);  // vérification physique : réservée aux rédactions
    }

    @Override
    protected void onPause() {
        handler.removeCallbacks(poller);
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        executor.shutdown();
        super.onDestroy();
    }

    private void loadFragment(Fragment fragment) {
        getSupportFragmentManager()
                .beginTransaction()
                .replace(R.id.fragmentContainer, fragment)
                .commit();
    }
}
