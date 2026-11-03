package com.hoeaona.mobile.verify;

import android.Manifest;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationManager;
import android.os.Build;
import androidx.core.content.ContextCompat;
import androidx.core.location.LocationManagerCompat;
import androidx.core.util.Consumer;
import com.hoeaona.mobile.api.ApiClient;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.Executors;

/**
 * Envoie la position du téléphone au serveur, uniquement si l'utilisateur a activé le partage.
 * Le serveur ne la renvoie jamais : elle sert seulement à PostGIS pour trouver qui est à moins de 2 km.
 */
public final class LocationReporter {
    private static final String PREFS = "hoe_settings";
    private static final String KEY_SHARING = "location_sharing";
    private static final long FRESH_MS = 10 * 60 * 1000;

    private LocationReporter() {}

    public static boolean isEnabled(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY_SHARING, false);
    }

    public static void setEnabled(Context context, boolean enabled) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        prefs.edit().putBoolean(KEY_SHARING, enabled).apply();
    }

    public static boolean hasPermission(Context context) {
        return ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
                || ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED;
    }

    public static boolean hasBackgroundPermission(Context context) {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.Q
                || ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_BACKGROUND_LOCATION) == PackageManager.PERMISSION_GRANTED;
    }

    /** Dernière position connue la plus récente, tous fournisseurs confondus. */
    public static Location lastKnown(Context context) {
        if (!hasPermission(context)) return null;
        LocationManager manager = (LocationManager) context.getSystemService(Context.LOCATION_SERVICE);
        Location best = null;
        try {
            for (String provider : manager.getProviders(true)) {
                Location l = manager.getLastKnownLocation(provider);
                if (l != null && (best == null || l.getTime() > best.getTime())) best = l;
            }
        } catch (SecurityException ignored) {
            return null;
        }
        return best;
    }

    /** Position actuelle : la dernière connue si elle est récente, sinon une mesure ponctuelle. */
    public static void current(Context context, Consumer<Location> callback) {
        Location last = lastKnown(context);
        if (last != null && System.currentTimeMillis() - last.getTime() < FRESH_MS) {
            callback.accept(last);
            return;
        }
        if (!hasPermission(context)) {
            callback.accept(null);
            return;
        }
        LocationManager manager = (LocationManager) context.getSystemService(Context.LOCATION_SERVICE);
        String provider = manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER) ? LocationManager.NETWORK_PROVIDER
                : manager.isProviderEnabled(LocationManager.GPS_PROVIDER) ? LocationManager.GPS_PROVIDER : null;
        if (provider == null) {
            callback.accept(last);
            return;
        }
        try {
            LocationManagerCompat.getCurrentLocation(manager, provider, (androidx.core.os.CancellationSignal) null,
                    ContextCompat.getMainExecutor(context), l -> callback.accept(l != null ? l : last));
        } catch (SecurityException e) {
            callback.accept(last);
        }
    }

    /** Premier plan : mesure la position et l'envoie si le partage est activé. */
    public static void reportAsync(Context context) {
        if (!isEnabled(context) || !hasPermission(context)) return;
        Context app = context.getApplicationContext();
        current(app, location -> {
            if (location != null) Executors.newSingleThreadExecutor().execute(() -> send(location));
        });
    }

    /** Arrière-plan (WorkManager) : dernière position connue seulement, appel bloquant. */
    public static void reportBlocking(Context context) {
        if (!isEnabled(context) || !hasBackgroundPermission(context)) return;
        Location location = lastKnown(context);
        if (location != null) send(location);
    }

    private static void send(Location location) {
        Map<String, Double> body = new HashMap<>();
        body.put("latitude", location.getLatitude());
        body.put("longitude", location.getLongitude());
        try {
            ApiClient.getApiService().updateLocation(body).execute();
        } catch (Exception ignored) {
            // nouvel essai au prochain cycle
        }
    }

    /** Désactivation : le téléphone cesse d'envoyer et le serveur efface la position. */
    public static void stopSharing(Context context) {
        setEnabled(context, false);
        Executors.newSingleThreadExecutor().execute(() -> {
            try {
                ApiClient.getApiService().stopSharingLocation().execute();
            } catch (Exception ignored) {
                // la position expire de toute façon côté serveur
            }
        });
    }
}
