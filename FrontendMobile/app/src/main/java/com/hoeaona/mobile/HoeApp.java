package com.hoeaona.mobile;

import android.app.Application;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.verify.VerificationNotifier;
import com.hoeaona.mobile.verify.VerificationWorker;
import org.osmdroid.config.Configuration;

public class HoeApp extends Application {
    private static HoeApp instance;

    public static HoeApp get() {
        return instance;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
        ApiClient.init(this);
        VerificationNotifier.createChannel(this);
        VerificationWorker.schedule(this);
        // Cartes OpenStreetMap : identifiant exigé par les serveurs de tuiles, cache dans le dossier de l'application.
        Configuration.getInstance().setUserAgentValue(BuildConfig.APPLICATION_ID);
        Configuration.getInstance().setOsmdroidBasePath(getCacheDir());
        Configuration.getInstance().setOsmdroidTileCache(new java.io.File(getCacheDir(), "tiles"));
    }
}
